"""Static, target-free semantic-authority registry for V0-075 production.

V1 registered an earlier, deliberately incomplete construction path.  This
module leaves V1 immutable and freezes the complete current production role
graph.  Readiness is derived by parsing committed module source: importing a
private runtime, loading a key, opening an observer, or accepting a producer's
claimed artifact/status is neither necessary nor permitted.

Historical aggregate ``PRODUCTION_INTEGRATION_READY`` flags are retained as
diagnostic facts where they exist.  They described older integrations and do
not override the exact API and safety-lock facts used by the current
occurrence chain.  The future campaign runner is a typed optional role: it is
NOT_READY while its module is absent and becomes mandatory as soon as that
module exists.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
)


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.43.0"
PROFILE_KEY = "v075_production_semantic_authority_registry_v2"

TARGET_EXECUTION_OPENED = False
PRIVATE_MATERIAL_IMPORTED = False
CALLER_SELF_ATTESTATION_ALLOWED = False
ARTIFACT_SEMANTIC_ATTESTATION_ALLOWED = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
WORKLOAD_ECONOMICS_GATE_STATUS = "NOT_RUN"
COUNTER_COMPLETENESS_GATE_STATUS = "NOT_RUN"
PREOPEN_V2_AUTHORIZATION_BOUND = False

_VERIFIER_MODULE = "acfqp.v075_production_semantic_authority_registry_v2"
_PACKAGE_ROOT = Path(__file__).resolve().parent

DOMAIN_TAGS = {
    "role_spec": "acfqp:v075-production-semantic-authority-role-spec:v2",
    "registry": "acfqp:v075-production-semantic-authority-registry:v2",
    "role_readiness": (
        "acfqp:v075-production-semantic-authority-role-readiness:v2"
    ),
    "readiness": (
        "acfqp:v075-production-semantic-authority-readiness:v2"
    ),
    "verification": (
        "acfqp:v075-production-semantic-authority-verification:v2"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 V2 registry domains overlap")


class V075ProductionSemanticAuthorityV2InvariantViolation(ValueError):
    """A static role graph, source surface, or replay was invalid."""


def _fail(message: str) -> None:
    raise V075ProductionSemanticAuthorityV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075ProductionSemanticAuthorityV2InvariantViolation(
            str(error)
        ) from error


class V075ProductionSemanticRoleV2(str, Enum):
    DEPENDENCY_LOCK = "DEPENDENCY_LOCK"
    PUBLIC_CAMPAIGN_NAMESPACE = "PUBLIC_CAMPAIGN_NAMESPACE"
    TRACKED_SOURCE = "TRACKED_SOURCE"
    SOURCE_PRIOR = "SOURCE_PRIOR"
    SOURCE_WORK = "SOURCE_WORK"
    PRIVATE_ENVIRONMENT_PROFILE = "PRIVATE_ENVIRONMENT_PROFILE"
    PRIVATE_SIGNER_RUNTIME = "PRIVATE_SIGNER_RUNTIME"
    REVEAL_VERIFYING_ATTESTATION = "REVEAL_VERIFYING_ATTESTATION"
    PREOPEN_AUTHORIZATION = "PREOPEN_AUTHORIZATION"
    OBSERVER_BOUNDARY = "OBSERVER_BOUNDARY"
    BATCHED_OBSERVER = "BATCHED_OBSERVER"
    MULTISTAGE_LIFECYCLE = "MULTISTAGE_LIFECYCLE"
    FAILURE_LIFECYCLE = "FAILURE_LIFECYCLE"
    PRODUCTION_OCCURRENCE_PLAN = "PRODUCTION_OCCURRENCE_PLAN"
    BATCH_NATIVE_BACKEND = "BATCH_NATIVE_BACKEND"
    BATCH_NATIVE_PLANNER = "BATCH_NATIVE_PLANNER"
    OPERATIONAL_TRANSPORT = "OPERATIONAL_TRANSPORT"
    PRODUCTION_OCCURRENCE_IPC = "PRODUCTION_OCCURRENCE_IPC"
    BATCH_NATIVE_TOTAL_LIFT = "BATCH_NATIVE_TOTAL_LIFT"
    PRODUCTION_OCCURRENCE_AUTHORITY = (
        "PRODUCTION_OCCURRENCE_AUTHORITY"
    )
    CAMPAIGN_RECONCILIATION = "CAMPAIGN_RECONCILIATION"
    COMPLETE_BUNDLE_ENDPOINT = "COMPLETE_BUNDLE_ENDPOINT"
    PRODUCTION_CAMPAIGN_RUNNER = "PRODUCTION_CAMPAIGN_RUNNER"


class V075StaticRoleReadinessV2(str, Enum):
    READY = "READY"
    OPTIONAL_NOT_READY_MODULE_ABSENT = "OPTIONAL_NOT_READY_MODULE_ABSENT"
    REQUIRED_NOT_READY = "REQUIRED_NOT_READY"


@dataclass(frozen=True, slots=True)
class V075RequiredConstantV2:
    name: str
    expected: Any

    def __post_init__(self) -> None:
        if (
            type(self.name) is not str
            or not self.name
            or not self.name.isidentifier()
            or type(self.expected)
            not in {bool, int, str, type(None)}
        ):
            _fail("registered readiness constant is malformed")

    def to_document(self) -> dict[str, Any]:
        return {"name": self.name, "expected": self.expected}


def _c(name: str, expected: Any) -> V075RequiredConstantV2:
    return V075RequiredConstantV2(name, expected)


@dataclass(frozen=True, slots=True)
class V075ProductionSemanticRoleSpecV2:
    ordinal: int
    role: V075ProductionSemanticRoleV2
    producer_module: str
    artifact_schemas: tuple[str, ...]
    artifact_domains: tuple[str, ...]
    semantic_verifier_id: str
    semantic_verifier_module: str
    prerequisite_roles: tuple[V075ProductionSemanticRoleV2, ...]
    required_symbols: tuple[str, ...]
    required_constants: tuple[V075RequiredConstantV2, ...]
    legacy_aggregate_constants: tuple[str, ...] = ()
    optional_until_module_exists: bool = False
    serialized_artifact_role: bool = True
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.role) is not V075ProductionSemanticRoleV2
            or type(self.producer_module) is not str
            or not self.producer_module.startswith("acfqp.v075_")
            or self.producer_module.count(".") != 1
            or type(self.artifact_schemas) is not tuple
            or len(set(self.artifact_schemas)) != len(
                self.artifact_schemas
            )
            or any(
                type(value) is not str
                or not value.startswith("acfqp.v075_")
                or not value.endswith((".v1", ".v2"))
                for value in self.artifact_schemas
            )
            or type(self.artifact_domains) is not tuple
            or len(self.artifact_domains) != len(self.artifact_schemas)
            or len(set(self.artifact_domains)) != len(
                self.artifact_domains
            )
            or any(
                type(value) is not str
                or not value.startswith("acfqp:v075-")
                or not value.endswith((":v1", ":v2"))
                for value in self.artifact_domains
            )
            or type(self.semantic_verifier_id) is not str
            or not self.semantic_verifier_id.startswith("verify_v075_")
            or not self.semantic_verifier_id.endswith("_v2")
            or type(self.semantic_verifier_module) is not str
            or type(self.prerequisite_roles) is not tuple
            or len(set(self.prerequisite_roles))
            != len(self.prerequisite_roles)
            or any(
                type(value) is not V075ProductionSemanticRoleV2
                for value in self.prerequisite_roles
            )
            or type(self.required_symbols) is not tuple
            or not self.required_symbols
            or len(set(self.required_symbols)) != len(
                self.required_symbols
            )
            or any(
                type(value) is not str or not value.isidentifier()
                for value in self.required_symbols
            )
            or type(self.required_constants) is not tuple
            or len({item.name for item in self.required_constants})
            != len(self.required_constants)
            or any(
                type(value) is not V075RequiredConstantV2
                for value in self.required_constants
            )
            or type(self.legacy_aggregate_constants) is not tuple
            or len(set(self.legacy_aggregate_constants))
            != len(self.legacy_aggregate_constants)
            or any(
                type(value) is not str or not value.isidentifier()
                for value in self.legacy_aggregate_constants
            )
            or type(self.optional_until_module_exists) is not bool
            or type(self.serialized_artifact_role) is not bool
            or (
                self.serialized_artifact_role
                and not self.artifact_schemas
            )
            or (
                not self.serialized_artifact_role
                and (
                    self.artifact_schemas
                    or self.artifact_domains
                )
            )
        ):
            _fail("V0-075 V2 role specification is malformed")
        object.__setattr__(
            self,
            "_spec_id",
            _hash("role_spec", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_semantic_role_spec.v2",
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "role": self.role.value,
            "producer_module": self.producer_module,
            "artifact_schemas": list(self.artifact_schemas),
            "artifact_domains": list(self.artifact_domains),
            "semantic_verifier_id": self.semantic_verifier_id,
            "semantic_verifier_module": self.semantic_verifier_module,
            "verifier_function": self.semantic_verifier_id,
            "verifier_scope": "STATIC_IMPLEMENTATION_SURFACE_ONLY",
            "artifact_semantic_attestation_allowed": False,
            "primary_artifact_schema": (
                self.artifact_schemas[0]
                if self.serialized_artifact_role
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "NON_SERIALIZABLE_RUNTIME",
                }
            ),
            "primary_artifact_domain": (
                self.artifact_domains[0]
                if self.serialized_artifact_role
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "NON_SERIALIZABLE_RUNTIME",
                }
            ),
            "artifact_declaration_modules": list(
                self.artifact_declaration_modules
            ),
            "artifact_declaration_exempt": (
                not self.serialized_artifact_role
            ),
            "implementation_repository_path": (
                "src/acfqp/"
                f"{self.producer_module.split('.', 1)[1]}.py"
            ),
            "implementation_blob_binding": "MANIFEST_SHA256_REQUIRED",
            "prerequisite_roles": [
                role.value for role in self.prerequisite_roles
            ],
            "required_symbols": list(self.required_symbols),
            "required_constants": [
                value.to_document() for value in self.required_constants
            ],
            "legacy_aggregate_constants": list(
                self.legacy_aggregate_constants
            ),
            "optional_until_module_exists": (
                self.optional_until_module_exists
            ),
            "serialized_artifact_role": self.serialized_artifact_role,
            "caller_self_attestation_allowed": False,
            "target_or_private_import_required": False,
        }

    @property
    def spec_id(self) -> str:
        return self._spec_id

    @property
    def verifier_module(self) -> str:
        return self.semantic_verifier_module

    @property
    def verifier_function(self) -> str:
        return self.semantic_verifier_id

    @property
    def artifact_schema(self) -> str | None:
        return (
            self.artifact_schemas[0]
            if self.serialized_artifact_role
            else None
        )

    @property
    def artifact_domain(self) -> str | None:
        return (
            self.artifact_domains[0]
            if self.serialized_artifact_role
            else None
        )

    @property
    def artifact_declaration_modules(self) -> tuple[str, ...]:
        if not self.serialized_artifact_role:
            return ()
        if (
            self.role
            is V075ProductionSemanticRoleV2
            .REVEAL_VERIFYING_ATTESTATION
        ):
            return ("acfqp.v075_preopen_target_authorization_v1",)
        return (self.producer_module,)

    @property
    def implementation_path(self) -> str:
        return (
            "src/acfqp/"
            f"{self.producer_module.split('.', 1)[1]}.py"
        )

    @property
    def implementation_blob_binding(self) -> str:
        return "MANIFEST_SHA256_REQUIRED"

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "spec_id": self.spec_id}


def _row(
    role: V075ProductionSemanticRoleV2,
    module: str,
    schemas: tuple[str, ...],
    domains: tuple[str, ...],
    prerequisites: tuple[V075ProductionSemanticRoleV2, ...],
    symbols: tuple[str, ...],
    *,
    constants: tuple[V075RequiredConstantV2, ...] = (),
    legacy: tuple[str, ...] = (),
    optional: bool = False,
    serialized: bool = True,
) -> tuple[Any, ...]:
    return (
        role,
        module,
        schemas,
        domains,
        f"verify_v075_{role.value.lower()}_semantic_surface_v2",
        _VERIFIER_MODULE,
        prerequisites,
        symbols,
        constants,
        legacy,
        optional,
        serialized,
    )


R = V075ProductionSemanticRoleV2

_ROLE_ROWS = (
    _row(
        R.DEPENDENCY_LOCK,
        "acfqp.v075_confirmatory_manifest_preregistration_v1",
        (
            "acfqp.v075_runtime_dependency_lock.v1",
            "acfqp.v075_runtime_dependency_lock_verification.v1",
        ),
        (
            "acfqp:v075-runtime-dependency-lock:v1",
            "acfqp:v075-runtime-dependency-lock-verification:v1",
        ),
        (),
        ("verify_and_bind_v075_dependency_lock_v1",),
    ),
    _row(
        R.PUBLIC_CAMPAIGN_NAMESPACE,
        "acfqp.v075_public_campaign_authority_v1",
        (
            "acfqp.v075_public_family_generation.v1",
            "acfqp.v075_law_free_target_tape_namespace.v1",
        ),
        (
            "acfqp:v075-public-family-generation:v1",
            "acfqp:v075-law-free-target-tape-namespace:v1",
        ),
        (R.DEPENDENCY_LOCK,),
        (
            "freeze_v075_public_family_generation_v1",
            "derive_public_target_tape_namespace_v1",
        ),
        constants=(
            _c("PRODUCTION_OBSERVER_OPEN_ALLOWED", False),
            _c("INDEPENDENT_FINAL_AUTHORITY_VERIFIER_IMPLEMENTED", False),
        ),
    ),
    _row(
        R.TRACKED_SOURCE,
        "acfqp.v075_tracked_source_authority_v1",
        (
            "acfqp.v075_tracked_source_authority_bundle.v1",
            "acfqp.v075_tracked_source_authority_bundle_verification.v1",
        ),
        (
            "acfqp:v075-tracked-source-authority-bundle:v1",
            "acfqp:v075-tracked-source-authority-bundle-verification:v1",
        ),
        (R.DEPENDENCY_LOCK,),
        ("verify_tracked_v075_source_authorities_v1",),
    ),
    _row(
        R.SOURCE_PRIOR,
        "acfqp.v075_source_prior_adapter_v1",
        (
            "acfqp.v075_source_prior_adapter.v1",
            "acfqp.v075_source_prior_adapter_verification.v1",
        ),
        (
            "acfqp:v075-source-prior-adapter:v1",
            "acfqp:v075-source-prior-adapter-verification:v1",
        ),
        (R.TRACKED_SOURCE,),
        (
            "load_v075_source_prior_adapter_v1",
            "verify_v075_source_prior_adapter_independently_v1",
        ),
    ),
    _row(
        R.SOURCE_WORK,
        "acfqp.v075_public_source_work_authority_v1",
        ("acfqp.v075_verified_public_source_work_bundle.v1",),
        ("acfqp:v075-verified-public-source-work-bundle:v1",),
        (R.TRACKED_SOURCE,),
        ("verify_v075_public_source_work_artifacts_v1",),
    ),
    _row(
        R.PRIVATE_ENVIRONMENT_PROFILE,
        "acfqp.v075_private_environment_generation_profile_v1",
        ("acfqp.v075_private_environment_generation_profile.v1",),
        ("acfqp:v075-private-environment-generation-profile:v1",),
        (R.PUBLIC_CAMPAIGN_NAMESPACE,),
        (
            "freeze_v075_private_environment_generation_profile_v1",
            "V075PrivateGeneratedEnvironmentV1",
        ),
        constants=(
            _c("PRODUCTION_LAW_SERIALIZED", False),
            _c("PRODUCTION_ENVIRONMENT_ID_SERIALIZED", False),
            _c("OBSERVER_OPENED", False),
            _c("TARGET_EXECUTION_ALLOWED", False),
        ),
    ),
    _row(
        R.PRIVATE_SIGNER_RUNTIME,
        "acfqp.v075_production_private_signer_runtime_v1",
        (),
        (),
        (R.PUBLIC_CAMPAIGN_NAMESPACE,),
        (
            "V075ProductionObserverEvidenceSignerV1",
            "load_v075_production_observer_evidence_signer_v1",
        ),
        constants=(
            _c("PRODUCTION_PRIVATE_SIGNER_RUNTIME_IMPLEMENTED", True),
            _c("PRIVATE_KEY_MATERIAL_SERIALIZED", False),
            _c("TARGET_EXECUTION_OPENED", False),
            _c("POSIX_SECURE_OPEN_REQUIRED", True),
        ),
        serialized=False,
    ),
    _row(
        R.REVEAL_VERIFYING_ATTESTATION,
        "acfqp.v075_reveal_verifying_attestation_authority_v1",
        ("acfqp.v075_private_reveal_attestation.v1",),
        ("acfqp:v075-private-reveal-attestation:v1",),
        (
            R.PUBLIC_CAMPAIGN_NAMESPACE,
            R.PRIVATE_ENVIRONMENT_PROFILE,
            R.PRIVATE_SIGNER_RUNTIME,
        ),
        (
            "issue_v075_reveal_verified_private_attestation_v1",
            "load_and_verify_v075_reveal_verified_attestation_v1",
        ),
        constants=(_c("TARGET_EXECUTION_OPENED", False),),
    ),
    _row(
        R.PREOPEN_AUTHORIZATION,
        "acfqp.v075_preopen_target_authorization_v1",
        (
            "acfqp.v075_observer_open_authorization.v1",
            "acfqp.v075_preopen_authorization_readiness.v1",
        ),
        (
            "acfqp:v075-observer-open-authorization:v1",
            "acfqp:v075-preopen-authorization-readiness:v1",
        ),
        (
            R.DEPENDENCY_LOCK,
            R.TRACKED_SOURCE,
            R.SOURCE_WORK,
            R.REVEAL_VERIFYING_ATTESTATION,
        ),
        (
            "load_and_verify_v075_private_reveal_attestation_v1",
            "verify_v075_observer_open_authorization_v1",
        ),
    ),
    _row(
        R.OBSERVER_BOUNDARY,
        "acfqp.v075_private_observer_boundary_v1",
        (
            "acfqp.v075_observer_open_authority_binding.v1",
            "acfqp.v075_append_only_observer_journal_closure.v1",
        ),
        (
            "acfqp:v075-observer-open-authority-binding:v1",
            "acfqp:v075-append-only-observer-journal-closure:v1",
        ),
        (
            R.PRIVATE_ENVIRONMENT_PROFILE,
            R.PRIVATE_SIGNER_RUNTIME,
            R.PREOPEN_AUTHORIZATION,
        ),
        (
            "open_private_observer_v1",
            "verify_private_observer_journal_closure_v1",
        ),
        constants=(
            _c("PRODUCTION_ENVIRONMENT_INCLUDED", False),
            _c("PRODUCTION_PRIVATE_SIGNER_INCLUDED", False),
            _c("PRODUCTION_OPEN_AUTHORITY_INCLUDED", False),
        ),
    ),
    _row(
        R.BATCHED_OBSERVER,
        "acfqp.v075_batched_observer_authority_v1",
        (
            "acfqp.v075_signed_observation_batch.v1",
            "acfqp.v075_batched_observation_private_replay_verification.v1",
        ),
        (
            "acfqp:v075-signed-observation-batch:v1",
            "acfqp:v075-batched-observation-private-replay-verification:v1",
        ),
        (R.OBSERVER_BOUNDARY,),
        (
            "verify_v075_signed_batched_observation_v1",
            "verify_v075_production_batched_observation_private_replay_v1",
        ),
    ),
    _row(
        R.MULTISTAGE_LIFECYCLE,
        "acfqp.v075_multistage_observer_lifecycle_v1",
        (
            "acfqp.v075_multistage_observer_occurrence_closure.v1",
            (
                "acfqp.v075_multistage_observer_occurrence_"
                "closure_verification.v1"
            ),
        ),
        (
            "acfqp:v075-multistage-observer-occurrence-closure:v1",
            (
                "acfqp:v075-multistage-observer-occurrence-"
                "closure-verification:v1"
            ),
        ),
        (R.BATCHED_OBSERVER,),
        (
            "open_v075_parent_owned_multistage_lifecycle_v1",
            "verify_v075_multistage_occurrence_closure_v1",
        ),
        constants=(_c("PER_DRAW_CAPABILITY_EXPANSION_ALLOWED", False),),
        legacy=("PRODUCTION_INTEGRATION_READY",),
    ),
    _row(
        R.FAILURE_LIFECYCLE,
        "acfqp.v075_occurrence_failure_lifecycle_authority_v1",
        (
            "acfqp.v075_occurrence_failure_lifecycle_closure.v1",
            "acfqp.v075_occurrence_failure_lifecycle_verification.v1",
        ),
        (
            "acfqp:v075-occurrence-failure-lifecycle-closure:v1",
            "acfqp:v075-occurrence-failure-lifecycle-verification:v1",
        ),
        (
            R.PRIVATE_ENVIRONMENT_PROFILE,
            R.OBSERVER_BOUNDARY,
            R.BATCHED_OBSERVER,
            R.MULTISTAGE_LIFECYCLE,
        ),
        (
            "open_v075_occurrence_failure_lifecycle_authority_v1",
            "verify_v075_production_occurrence_failure_lifecycle_v1",
        ),
        constants=(
            _c("TARGET_EXECUTION_OPENED", False),
            _c("PLAN_CERTIFICATE_ALLOWED", False),
            _c("INFEASIBILITY_CERTIFICATE_ALLOWED", False),
        ),
    ),
    _row(
        R.PRODUCTION_OCCURRENCE_PLAN,
        "acfqp.v075_production_occurrence_plan_v1",
        (
            "acfqp.v075_production_occurrence_plan.v1",
            "acfqp.v075_production_occurrence_plan_verification.v1",
        ),
        (
            "acfqp:v075-production-occurrence-plan:v1",
            "acfqp:v075-production-occurrence-plan-verification:v1",
        ),
        (
            R.PUBLIC_CAMPAIGN_NAMESPACE,
            R.TRACKED_SOURCE,
            R.SOURCE_PRIOR,
        ),
        (
            "freeze_v075_production_occurrence_plan_v1",
            "verify_v075_production_occurrence_plan_bytes_v1",
        ),
        constants=(_c("EXPECTED_OCCURRENCE_COUNT", 15),),
    ),
    _row(
        R.BATCH_NATIVE_BACKEND,
        "acfqp.v075_batch_native_statistical_backend_v1",
        ("acfqp.v075_batch_native_backend_result.v1",),
        ("acfqp:v075-batch-native-backend-result:v1",),
        (R.BATCHED_OBSERVER, R.PRODUCTION_OCCURRENCE_PLAN),
        (
            "compile_v075_batch_native_statistical_backend_v1",
            "verify_v075_batch_native_backend_result_v1",
        ),
        constants=(_c("PER_DRAW_CAPABILITY_EXPANSION_ALLOWED", False),),
        legacy=("PRODUCTION_INTEGRATION_READY",),
    ),
    _row(
        R.BATCH_NATIVE_PLANNER,
        "acfqp.v075_learned_support_quotient_planners_v1",
        (
            "acfqp.v075_learned_support_graph.v1",
            "acfqp.v075_support_planner_result.v1",
        ),
        (
            "acfqp:v075-learned-support-graph:v1",
            "acfqp:v075-support-planner-result:v1",
        ),
        (R.BATCH_NATIVE_BACKEND,),
        (
            "plan_v075_exact_h2_abstract_v1",
            "plan_v075_exact_h2_matched_direct_ground_v1",
            "verify_v075_abstract_planner_result_v1",
            "verify_v075_matched_direct_planner_result_v1",
        ),
        constants=(_c("SCIENTIFIC_CERTIFICATE_ISSUANCE_ALLOWED", False),),
        legacy=("PRODUCTION_INTEGRATION_READY",),
    ),
    _row(
        R.OPERATIONAL_TRANSPORT,
        "acfqp.v075_operational_planner_transport_v1",
        (
            "acfqp.v075_operational_planner_transport.v1",
            "acfqp.v075_operational_planner_load.v1",
        ),
        (
            "acfqp:v075-operational-planner-transport:v1",
            "acfqp:v075-operational-planner-load:v1",
        ),
        (R.BATCH_NATIVE_BACKEND, R.BATCH_NATIVE_PLANNER),
        (
            "freeze_v075_operational_planner_transport_v1",
            "load_v075_operational_planner_transport_v1",
        ),
        constants=(
            _c("MODEL_COMPILATION_ALLOWED", False),
            _c("PLANNER_EXECUTION_ALLOWED", False),
            _c("SOLVER_OR_SEARCH_ALLOWED", False),
            _c("PRIVATE_MATERIAL_ALLOWED", False),
        ),
    ),
    _row(
        R.PRODUCTION_OCCURRENCE_IPC,
        "acfqp.v075_production_occurrence_ipc_v1",
        (
            "acfqp.v075_production_occurrence_ipc_result.v1",
            (
                "acfqp.v075_production_occurrence_ipc_"
                "standalone_verification.v1"
            ),
        ),
        (
            "acfqp:v075-production-occurrence-ipc-result:v1",
            (
                "acfqp:v075-production-occurrence-ipc-"
                "standalone-verification:v1"
            ),
        ),
        (
            R.PREOPEN_AUTHORIZATION,
            R.MULTISTAGE_LIFECYCLE,
            R.PRODUCTION_OCCURRENCE_PLAN,
            R.OPERATIONAL_TRANSPORT,
        ),
        (
            "execute_v075_production_occurrence_ipc_v1",
            "verify_v075_occurrence_ipc_result_standalone_v1",
        ),
        constants=(
            _c("PRODUCTION_TRANSPORT_READY", True),
            _c("MATCHED_DIRECT_HANDLER_READY", True),
            _c("TARGET_EXECUTION_OPENED", False),
            _c("PRIVATE_MATERIAL_TRANSPORT_ALLOWED", False),
            _c("PICKLE_TRANSPORT_ALLOWED", False),
            _c("HOST_OPERATIONAL_FULL_PLANNER_REPLAY_ALLOWED", False),
        ),
        legacy=("PRODUCTION_OCCURRENCE_WORKER_COMPLETE",),
    ),
    _row(
        R.BATCH_NATIVE_TOTAL_LIFT,
        "acfqp.v075_batch_native_total_lift_authority_v1",
        (
            "acfqp.v075_batch_native_total_lift_production_result.v1",
            "acfqp.v075_batch_native_total_lift_production_readiness.v1",
        ),
        (
            "acfqp:v075-batch-native-total-lift-production-result:v1",
            "acfqp:v075-batch-native-total-lift-production-readiness:v1",
        ),
        (
            R.MULTISTAGE_LIFECYCLE,
            R.BATCH_NATIVE_BACKEND,
            R.BATCH_NATIVE_PLANNER,
            R.OPERATIONAL_TRANSPORT,
        ),
        (
            "evaluate_v075_batch_native_production_total_lift_v1",
            "verify_v075_batch_native_production_total_lift_candidate_v1",
        ),
        constants=(
            _c(
                "CANONICAL_BACKEND_RECOMPUTATION_IN_OPERATIONAL_BRIDGE",
                False,
            ),
            _c(
                "CANONICAL_PLANNER_RECOMPUTATION_IN_OPERATIONAL_BRIDGE",
                False,
            ),
            _c("PER_DRAW_CAPABILITY_EXPANSION_ALLOWED", False),
        ),
        legacy=("PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED",),
    ),
    _row(
        R.PRODUCTION_OCCURRENCE_AUTHORITY,
        "acfqp.v075_production_occurrence_authority_v1",
        (
            "acfqp.v075_production_occurrence_authority_result.v1",
            "acfqp.v075_production_occurrence_authority_verification.v1",
        ),
        (
            "acfqp:v075-production-occurrence-authority-result:v1",
            (
                "acfqp:v075-production-occurrence-authority-"
                "verification:v1"
            ),
        ),
        (
            R.FAILURE_LIFECYCLE,
            R.PRODUCTION_OCCURRENCE_PLAN,
            R.PRODUCTION_OCCURRENCE_IPC,
            R.BATCH_NATIVE_TOTAL_LIFT,
        ),
        (
            "execute_v075_production_occurrence_v1",
            "verify_v075_production_occurrence_authority_result_v1",
        ),
        constants=(
            _c("TARGET_EXECUTION_OPENED", False),
            _c("HOST_MODEL_COMPILATION_ALLOWED", False),
            _c("HOST_PLANNER_EXECUTION_ALLOWED", False),
            _c("HOST_SOLVER_OR_SEARCH_ALLOWED", False),
            _c("PRIVATE_MATERIAL_SERIALIZATION_ALLOWED", False),
        ),
    ),
    _row(
        R.CAMPAIGN_RECONCILIATION,
        "acfqp.v075_production_campaign_reconciliation_v1",
        (
            "acfqp.v075_production_campaign_reconciliation.v1",
            (
                "acfqp.v075_production_campaign_reconciliation_"
                "verification.v1"
            ),
        ),
        (
            "acfqp:v075-production-campaign-reconciliation:v1",
            (
                "acfqp:v075-production-campaign-reconciliation-"
                "verification:v1"
            ),
        ),
        (
            R.SOURCE_WORK,
            R.PRODUCTION_OCCURRENCE_PLAN,
            R.PRODUCTION_OCCURRENCE_AUTHORITY,
        ),
        (
            "reconcile_v075_production_campaign_v1",
            "verify_v075_production_campaign_reconciliation_v1",
        ),
        constants=(
            _c("TARGET_EXECUTION_OPENED", False),
            _c("CALLER_SUMMARIES_ACCEPTED", False),
            _c("CALLER_TOTALS_ACCEPTED", False),
            _c("REORDERING_ACCEPTED", False),
            _c("OFFICIAL_EXECUTION_ALLOWED", False),
            _c("OFFICIAL_SCALAR_COST", None),
            _c("OFFICIAL_N_BREAK_EVEN", None),
            _c("WORKLOAD_ECONOMICS_GATE_STATUS", "NOT_RUN"),
            _c("COUNTER_COMPLETENESS_GATE_STATUS", "NOT_RUN"),
        ),
    ),
    _row(
        R.COMPLETE_BUNDLE_ENDPOINT,
        "acfqp.v075_production_complete_bundle_endpoint_v1",
        (
            "acfqp.v075_production_complete_bundle_endpoint_verification.v1",
        ),
        (
            "acfqp:v075-production-complete-bundle-endpoint-"
            "verification:v1",
        ),
        (R.CAMPAIGN_RECONCILIATION,),
        ("verify_v075_production_complete_bundle_endpoint_v1",),
        constants=(
            _c("PRODUCTION_COMPLETE_BUNDLE_PROTOCOL_STATUS", "READY"),
            _c("PRODUCTION_ENDPOINT_VERIFICATION_ALLOWED", True),
            _c("TARGET_EXECUTION_OPENED", False),
            _c("PRIVATE_TARGET_INPUTS_ACCEPTED", False),
            _c("CALLER_VERDICTS_ACCEPTED", False),
            _c("CALLER_TOTALS_ACCEPTED", False),
            _c("OFFICIAL_EXECUTION_ALLOWED", False),
            _c("OFFICIAL_SCALAR_COST", None),
            _c("OFFICIAL_N_BREAK_EVEN", None),
            _c("WORKLOAD_ECONOMICS_GATE_STATUS", "NOT_RUN"),
            _c("COUNTER_COMPLETENESS_GATE_STATUS", "NOT_RUN"),
        ),
    ),
    _row(
        R.PRODUCTION_CAMPAIGN_RUNNER,
        "acfqp.v075_production_campaign_runner_v1",
        (
            "acfqp.v075_production_campaign_run.v1",
            "acfqp.v075_production_campaign_run_verification.v1",
        ),
        (
            "acfqp:v075-production-campaign-run:v1",
            "acfqp:v075-production-campaign-run-verification:v1",
        ),
        (
            R.PUBLIC_CAMPAIGN_NAMESPACE,
            R.MULTISTAGE_LIFECYCLE,
            R.PRODUCTION_OCCURRENCE_PLAN,
            R.PRIVATE_SIGNER_RUNTIME,
            R.PRODUCTION_OCCURRENCE_AUTHORITY,
            R.CAMPAIGN_RECONCILIATION,
            R.COMPLETE_BUNDLE_ENDPOINT,
        ),
        (
            "freeze_v075_production_campaign_runner_profile_v1",
            "bind_v075_production_occurrence_execution_input_v1",
            "run_v075_production_campaign_v1",
            "verify_v075_production_campaign_run_v1",
        ),
        constants=(
            _c("PRODUCTION_CAMPAIGN_RUNNER_READY", True),
            _c("TARGET_EXECUTION_OPENED", False),
            _c("OFFICIAL_EXECUTION_ALLOWED", False),
            _c("OFFICIAL_SCALAR_COST", None),
            _c("OFFICIAL_N_BREAK_EVEN", None),
            _c("WORKLOAD_ECONOMICS_GATE_STATUS", "NOT_RUN"),
            _c("COUNTER_COMPLETENESS_GATE_STATUS", "NOT_RUN"),
        ),
        optional=True,
    ),
)


def _registered_semantic_surface_verifier_v2(
    spec: V075ProductionSemanticRoleSpecV2,
    *,
    package_root: Path,
) -> "V075SemanticRoleReadinessRecordV2":
    """Independent verifier implementation shared by typed role entries."""

    return _audit_role(spec, package_root=package_root)


_SEMANTIC_VERIFIER_FUNCTIONS = {
    row[4]: _registered_semantic_surface_verifier_v2
    for row in _ROLE_ROWS
}
_KNOWN_SEMANTIC_VERIFIERS = frozenset(
    _SEMANTIC_VERIFIER_FUNCTIONS
)


def canonical_v075_production_semantic_role_specs_v2(
) -> tuple[V075ProductionSemanticRoleSpecV2, ...]:
    return tuple(
        V075ProductionSemanticRoleSpecV2(index, *row)
        for index, row in enumerate(_ROLE_ROWS)
    )


def resolve_v075_production_semantic_verifier_v2(
    spec: V075ProductionSemanticRoleSpecV2,
) -> Any:
    """Resolve only a registry-owned executable verifier, never a producer."""

    if type(spec) is not V075ProductionSemanticRoleSpecV2:
        _fail("semantic verifier resolution requires one typed role spec")
    verifier = _SEMANTIC_VERIFIER_FUNCTIONS.get(spec.semantic_verifier_id)
    if (
        spec.semantic_verifier_module != _VERIFIER_MODULE
        or spec.semantic_verifier_module == spec.producer_module
        or not callable(verifier)
    ):
        _fail("semantic verifier is unknown or producer self-attested")
    return verifier


@dataclass(frozen=True, slots=True)
class V075ProductionSemanticAuthorityRegistryV2:
    role_specs: tuple[V075ProductionSemanticRoleSpecV2, ...]
    _registry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _validate_role_graph(self.role_specs)
        object.__setattr__(
            self,
            "_registry_id",
            _hash("registry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_semantic_authority_registry.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "role_order": [spec.role.value for spec in self.role_specs],
            "role_spec_ids": [spec.spec_id for spec in self.role_specs],
            "role_count": len(self.role_specs),
            "caller_self_attestation_allowed": False,
            "artifact_semantic_attestation_allowed": False,
            "registered_verifier_scope": (
                "STATIC_IMPLEMENTATION_SURFACE_ONLY"
            ),
            "role_specific_artifact_replay_still_required": True,
            "producer_status_string_is_evidence": False,
            "producer_content_id_is_evidence": False,
            "source_ast_replay_required": True,
            "target_import_required": False,
            "private_material_import_required": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "NOT_RUN",
        }

    @property
    def registry_id(self) -> str:
        return self._registry_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "role_specs": [spec.to_document() for spec in self.role_specs],
            "registry_id": self.registry_id,
        }


def _validate_role_graph(
    specs: Sequence[V075ProductionSemanticRoleSpecV2],
) -> None:
    if type(specs) not in {tuple, list} or not specs:
        _fail("semantic role graph is absent")
    if any(
        type(spec) is not V075ProductionSemanticRoleSpecV2
        for spec in specs
    ):
        _fail("semantic role graph contains an untyped role")
    roles = tuple(spec.role for spec in specs)
    if len(set(roles)) != len(roles):
        _fail("semantic authority role is reused")
    if tuple(spec.ordinal for spec in specs) != tuple(range(len(specs))):
        _fail("semantic role ordinals are not continuous")
    role_set = set(roles)
    domains: set[str] = set()
    schemas: set[str] = set()
    prior: set[V075ProductionSemanticRoleV2] = set()
    for spec in specs:
        if not set(spec.prerequisite_roles) <= role_set:
            _fail("semantic authority dependency is missing")
        if not set(spec.prerequisite_roles) <= prior:
            _fail("semantic authority dependency graph is cyclic or forward")
        if domains & set(spec.artifact_domains):
            _fail("semantic authority artifact domain collision")
        if schemas & set(spec.artifact_schemas):
            _fail("semantic authority artifact schema collision")
        domains.update(spec.artifact_domains)
        schemas.update(spec.artifact_schemas)
        prior.add(spec.role)
        if spec.semantic_verifier_id not in _KNOWN_SEMANTIC_VERIFIERS:
            _fail("semantic authority references an unknown verifier")
        if not callable(
            _SEMANTIC_VERIFIER_FUNCTIONS.get(spec.semantic_verifier_id)
        ):
            _fail("semantic authority verifier is not executable")
        if (
            spec.semantic_verifier_module != _VERIFIER_MODULE
            or spec.semantic_verifier_module == spec.producer_module
        ):
            _fail("producer self-attestation is forbidden")
    if set(prior) != role_set:
        _fail("semantic authority dependency closure is incomplete")


def freeze_v075_production_semantic_authority_registry_v2(
) -> V075ProductionSemanticAuthorityRegistryV2:
    return V075ProductionSemanticAuthorityRegistryV2(
        canonical_v075_production_semantic_role_specs_v2()
    )


@dataclass(frozen=True, slots=True)
class _StaticModuleSurfaceV2:
    exists: bool
    symbols: frozenset[str]
    literal_constants: Mapping[str, Any]
    string_literals: frozenset[str]


def _module_path(
    module_name: str,
    *,
    package_root: Path,
) -> Path:
    if (
        type(module_name) is not str
        or not module_name.startswith("acfqp.")
        or module_name.count(".") != 1
    ):
        _fail("producer module name is malformed")
    return package_root / f"{module_name.split('.', 1)[1]}.py"


def _read_static_module_surface(
    module_name: str,
    *,
    package_root: Path,
) -> _StaticModuleSurfaceV2:
    path = _module_path(module_name, package_root=package_root)
    if not path.is_file():
        return _StaticModuleSurfaceV2(
            False,
            frozenset(),
            {},
            frozenset(),
        )
    try:
        raw = path.read_bytes()
        if not raw or len(raw) > 16 * 1024 * 1024:
            _fail("semantic authority source is empty or over cap")
        tree = ast.parse(raw, filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as error:
        raise V075ProductionSemanticAuthorityV2InvariantViolation(
            f"cannot statically inspect {module_name}: {error}"
        ) from error
    symbols: set[str] = set()
    constants: dict[str, Any] = {}
    string_literals = frozenset(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and type(node.value) is str
    )
    for node in tree.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ):
            symbols.add(node.name)
        elif isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbols.add(target.id)
                    constants[target.id] = value
        elif isinstance(node, ast.AnnAssign) and isinstance(
            node.target, ast.Name
        ):
            symbols.add(node.target.id)
            if node.value is not None:
                try:
                    constants[node.target.id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    pass
    return _StaticModuleSurfaceV2(
        True,
        frozenset(symbols),
        constants,
        string_literals,
    )


@dataclass(frozen=True, slots=True)
class V075SemanticRoleReadinessRecordV2:
    role: V075ProductionSemanticRoleV2
    spec_id: str
    status: V075StaticRoleReadinessV2
    module_exists: bool
    missing_symbols: tuple[str, ...]
    mismatched_constants: tuple[str, ...]
    missing_artifact_declarations: tuple[str, ...]
    artifact_declarations_verified: bool
    artifact_declaration_exempt: bool
    legacy_aggregate_facts: tuple[tuple[str, Any], ...]
    _record_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.role) is not V075ProductionSemanticRoleV2
            or type(self.spec_id) is not str
            or len(self.spec_id) != 64
            or type(self.status) is not V075StaticRoleReadinessV2
            or type(self.module_exists) is not bool
            or self.missing_symbols
            != tuple(sorted(set(self.missing_symbols)))
            or self.mismatched_constants
            != tuple(sorted(set(self.mismatched_constants)))
            or self.missing_artifact_declarations
            != tuple(sorted(set(self.missing_artifact_declarations)))
            or type(self.artifact_declarations_verified) is not bool
            or type(self.artifact_declaration_exempt) is not bool
            or self.artifact_declarations_verified
            != (
                self.artifact_declaration_exempt
                or not self.missing_artifact_declarations
            )
            or tuple(name for name, _ in self.legacy_aggregate_facts)
            != tuple(
                sorted(
                    {name for name, _ in self.legacy_aggregate_facts}
                )
            )
            or (
                self.status is V075StaticRoleReadinessV2.READY
                and (
                    not self.module_exists
                    or self.missing_symbols
                    or self.mismatched_constants
                    or not self.artifact_declarations_verified
                )
            )
        ):
            _fail("semantic role readiness record is inconsistent")
        object.__setattr__(
            self,
            "_record_id",
            _hash("role_readiness", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_semantic_role_readiness.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "role": self.role.value,
            "spec_id": self.spec_id,
            "status": self.status.value,
            "module_exists": self.module_exists,
            "missing_symbols": list(self.missing_symbols),
            "mismatched_constants": list(self.mismatched_constants),
            "missing_artifact_declarations": list(
                self.missing_artifact_declarations
            ),
            "artifact_declarations_verified": (
                self.artifact_declarations_verified
            ),
            "artifact_declaration_exempt": (
                self.artifact_declaration_exempt
            ),
            "legacy_aggregate_facts": [
                {"name": name, "observed": observed}
                for name, observed in self.legacy_aggregate_facts
            ],
            "legacy_aggregate_facts_are_readiness_authority": False,
            "producer_claims_accepted": False,
            "source_imported": False,
            "target_opened": False,
            "private_material_imported": False,
        }

    @property
    def record_id(self) -> str:
        return self._record_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "record_id": self.record_id}


def _audit_role(
    spec: V075ProductionSemanticRoleSpecV2,
    *,
    package_root: Path,
) -> V075SemanticRoleReadinessRecordV2:
    surface = _read_static_module_surface(
        spec.producer_module,
        package_root=package_root,
    )
    if not surface.exists:
        status = (
            V075StaticRoleReadinessV2.OPTIONAL_NOT_READY_MODULE_ABSENT
            if spec.optional_until_module_exists
            else V075StaticRoleReadinessV2.REQUIRED_NOT_READY
        )
        return V075SemanticRoleReadinessRecordV2(
            spec.role,
            spec.spec_id,
            status,
            False,
            tuple(sorted(spec.required_symbols)),
            tuple(sorted(item.name for item in spec.required_constants)),
            tuple(
                sorted(
                    {
                        *spec.artifact_schemas,
                        *spec.artifact_domains,
                    }
                )
            ),
            not spec.serialized_artifact_role,
            not spec.serialized_artifact_role,
            (),
        )
    missing = tuple(
        sorted(set(spec.required_symbols) - set(surface.symbols))
    )
    mismatched = tuple(
        sorted(
            requirement.name
            for requirement in spec.required_constants
            if (
                requirement.name not in surface.literal_constants
                or type(surface.literal_constants[requirement.name])
                is not type(requirement.expected)
                or surface.literal_constants[requirement.name]
                != requirement.expected
            )
        )
    )
    declaration_literals: set[str] = set()
    missing_declaration_module = False
    for module_name in spec.artifact_declaration_modules:
        declaration_surface = _read_static_module_surface(
            module_name,
            package_root=package_root,
        )
        if not declaration_surface.exists:
            missing_declaration_module = True
        declaration_literals.update(declaration_surface.string_literals)
    expected_declarations = {
        *spec.artifact_schemas,
        *spec.artifact_domains,
    }
    missing_declarations = tuple(
        sorted(expected_declarations - declaration_literals)
    )
    declarations_verified = (
        not spec.serialized_artifact_role
        or (
            not missing_declaration_module
            and not missing_declarations
        )
    )
    legacy = tuple(
        sorted(
            (
                name,
                surface.literal_constants.get(name, "UNRESOLVED"),
            )
            for name in spec.legacy_aggregate_constants
        )
    )
    status = (
        V075StaticRoleReadinessV2.READY
        if (
            not missing
            and not mismatched
            and declarations_verified
        )
        else V075StaticRoleReadinessV2.REQUIRED_NOT_READY
    )
    return V075SemanticRoleReadinessRecordV2(
        spec.role,
        spec.spec_id,
        status,
        True,
        missing,
        mismatched,
        missing_declarations,
        declarations_verified,
        not spec.serialized_artifact_role,
        legacy,
    )


@dataclass(frozen=True, slots=True)
class V075ProductionSemanticReadinessAuditV2:
    registry_id: str
    role_records: tuple[V075SemanticRoleReadinessRecordV2, ...]
    static_dependency_closure_valid: bool
    all_required_surfaces_ready: bool
    runner_ready: bool
    preopen_v2_migration_ready: bool
    production_semantic_chain_ready: bool
    blockers: tuple[str, ...]
    _audit_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.registry_id) is not str
            or len(self.registry_id) != 64
            or type(self.role_records) is not tuple
            or len(self.role_records) != len(V075ProductionSemanticRoleV2)
            or tuple(item.role for item in self.role_records)
            != tuple(V075ProductionSemanticRoleV2)
            or type(self.static_dependency_closure_valid) is not bool
            or type(self.all_required_surfaces_ready) is not bool
            or type(self.runner_ready) is not bool
            or type(self.preopen_v2_migration_ready) is not bool
            or type(self.production_semantic_chain_ready) is not bool
            or self.blockers != tuple(sorted(set(self.blockers)))
            or self.production_semantic_chain_ready
            != (
                self.static_dependency_closure_valid
                and self.all_required_surfaces_ready
                and self.runner_ready
                and self.preopen_v2_migration_ready
            )
        ):
            _fail("semantic readiness audit is inconsistent")
        object.__setattr__(
            self,
            "_audit_id",
            _hash("readiness", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_semantic_authority_readiness.v2"
            ),
            "schema_version": SCHEMA_VERSION,
            "registry_id": self.registry_id,
            "role_record_ids": [
                item.record_id for item in self.role_records
            ],
            "static_dependency_closure_valid": (
                self.static_dependency_closure_valid
            ),
            "all_required_surfaces_ready": (
                self.all_required_surfaces_ready
            ),
            "runner_ready": self.runner_ready,
            "preopen_v2_migration_ready": (
                self.preopen_v2_migration_ready
            ),
            "production_semantic_chain_ready": (
                self.production_semantic_chain_ready
            ),
            "blockers": list(self.blockers),
            "caller_self_attestation_allowed": False,
            "artifact_semantic_attestation_allowed": False,
            "role_specific_artifact_replay_still_required": True,
            "target_opened": False,
            "private_material_imported": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "workload_economics_gate_status": "NOT_RUN",
            "counter_completeness_gate_status": "NOT_RUN",
        }

    @property
    def audit_id(self) -> str:
        return self._audit_id

    @property
    def verification_id(self) -> str:
        return self._audit_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "role_records": [
                item.to_document() for item in self.role_records
            ],
            "audit_id": self.audit_id,
            "verification_id": self.verification_id,
        }

    def to_canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def verify_v075_production_semantic_authority_registry_v2(
    registry: V075ProductionSemanticAuthorityRegistryV2 | None = None,
    *,
    package_root: Path | None = None,
) -> V075ProductionSemanticReadinessAuditV2:
    """Rebuild the exact graph, then inspect source without importing it."""

    expected = freeze_v075_production_semantic_authority_registry_v2()
    candidate = expected if registry is None else registry
    if (
        type(candidate) is not V075ProductionSemanticAuthorityRegistryV2
        or candidate != expected
        or candidate.registry_id != expected.registry_id
    ):
        _fail("semantic registry is not the exact frozen V2 role graph")
    root = _PACKAGE_ROOT if package_root is None else package_root
    if not isinstance(root, Path) or not root.is_dir():
        _fail("semantic source package root is absent")
    records = tuple(
        _SEMANTIC_VERIFIER_FUNCTIONS[spec.semantic_verifier_id](
            spec,
            package_root=root,
        )
        for spec in candidate.role_specs
    )
    runner_record = records[list(R).index(R.PRODUCTION_CAMPAIGN_RUNNER)]
    required_records = tuple(
        record
        for record, spec in zip(records, candidate.role_specs, strict=True)
        if not spec.optional_until_module_exists
    )
    all_required_ready = all(
        record.status is V075StaticRoleReadinessV2.READY
        for record in required_records
    )
    runner_ready = (
        runner_record.status is V075StaticRoleReadinessV2.READY
    )
    blockers = tuple(
        sorted(
            {
                *(
                    f"{record.role.value}:{record.status.value}"
                    for record in records
                    if (
                        record.status
                        is not V075StaticRoleReadinessV2.READY
                    )
                ),
                "PREOPEN_V2_MIGRATION_NOT_READY",
            }
        )
    )
    return V075ProductionSemanticReadinessAuditV2(
        candidate.registry_id,
        records,
        True,
        all_required_ready,
        runner_ready,
        PREOPEN_V2_AUTHORIZATION_BOUND,
        (
            all_required_ready
            and runner_ready
            and PREOPEN_V2_AUTHORIZATION_BOUND
        ),
        blockers,
    )


def load_and_verify_v075_production_semantic_readiness_v2(
    raw: bytes,
    *,
    registry: V075ProductionSemanticAuthorityRegistryV2 | None = None,
    package_root: Path | None = None,
) -> V075ProductionSemanticReadinessAuditV2:
    """Reject stale or caller-authored readiness; independently rederive it."""

    if type(raw) is not bytes or not raw or len(raw) > 4 * 1024 * 1024:
        _fail("semantic readiness bytes are absent, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075ProductionSemanticAuthorityV2InvariantViolation(
            f"semantic readiness document is invalid: {error}"
        ) from error
    current = verify_v075_production_semantic_authority_registry_v2(
        registry,
        package_root=package_root,
    )
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != raw
        or document != current.to_document()
    ):
        _fail("semantic readiness is stale, forged, or self-attested")
    return current


__all__ = [
    "CALLER_SELF_ATTESTATION_ALLOWED",
    "ARTIFACT_SEMANTIC_ATTESTATION_ALLOWED",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "DOMAIN_TAGS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "PRIVATE_MATERIAL_IMPORTED",
    "PREOPEN_V2_AUTHORIZATION_BOUND",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "TARGET_EXECUTION_OPENED",
    "V075ProductionSemanticAuthorityRegistryV2",
    "V075ProductionSemanticAuthorityV2InvariantViolation",
    "V075ProductionSemanticReadinessAuditV2",
    "V075ProductionSemanticRoleSpecV2",
    "V075ProductionSemanticRoleV2",
    "V075RequiredConstantV2",
    "V075SemanticRoleReadinessRecordV2",
    "V075StaticRoleReadinessV2",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "canonical_v075_production_semantic_role_specs_v2",
    "freeze_v075_production_semantic_authority_registry_v2",
    "load_and_verify_v075_production_semantic_readiness_v2",
    "resolve_v075_production_semantic_verifier_v2",
    "verify_v075_production_semantic_authority_registry_v2",
]
