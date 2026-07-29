"""Independent semantic-authority registry for the V0-075 production path.

This module does not make any production component ready.  It gives each
public authority role one typed schema/domain assignment, independently
replays the public artifacts that already exist, and derives the remaining
production blockers from executable/type/import facts rather than accepting
claimed status strings or content identifiers.

The registry deliberately has no top-level dependency on the occurrence
worker, route backend, private generator, total-lift authority,
reconciliation, or complete-bundle endpoint.  Those components are imported
only inside their role verifier.  This keeps the verifier boundary usable for
dependency audits and prevents importing a legacy source runtime merely by
importing this module.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import importlib
import inspect
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_public_campaign_authority_v1 as public_authority


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_production_semantic_authority_registry_v1"
COMMITTED_ARTIFACT_PATH_REPLAY_IMPLEMENTED = False

DOMAIN_TAGS = {
    "role_spec": "acfqp:v075-production-semantic-role-spec:v1",
    "registry": "acfqp:v075-production-semantic-authority-registry:v1",
    "dependency_closure": (
        "acfqp:v075-production-semantic-dependency-closure:v1"
    ),
    "verification": (
        "acfqp:v075-production-semantic-artifact-verification:v1"
    ),
    "readiness": "acfqp:v075-production-semantic-readiness-audit:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 semantic-authority domains must be unique")


class V075ProductionSemanticAuthorityInvariantViolation(ValueError):
    """A role, artifact, dependency, or semantic replay was invalid."""


class V075ProductionSemanticAuthorityNotReady(RuntimeError):
    """The independently derived production dependency graph is not ready."""


def _fail(message: str) -> None:
    raise V075ProductionSemanticAuthorityInvariantViolation(message)


def _hash(domain: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            domain.encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (TypeError, ValueError) as error:
        raise V075ProductionSemanticAuthorityInvariantViolation(
            str(error)
        ) from error


def _registry_hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return _hash(DOMAIN_TAGS[role], payload)
    except KeyError as error:  # pragma: no cover - frozen internal call graph
        raise RuntimeError("unknown semantic-authority domain") from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075ProductionSemanticAuthorityInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _canonical_document(
    raw: bytes,
    *,
    field_name: str,
    byte_cap: int = 4 * 1024 * 1024,
) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > byte_cap:
        _fail(f"{field_name} bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
        if (
            type(document) is not dict
            or canonical_json_bytes(document) != raw
        ):
            _fail(f"{field_name} is not one canonical object")
        return document
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075ProductionSemanticAuthorityInvariantViolation(
            f"{field_name} is invalid: {error}"
        ) from error


def _recompute_document_id(
    document: Mapping[str, Any],
    *,
    domain: str,
    id_field: str,
) -> str:
    if type(document) is not dict or id_field not in document:
        _fail(f"{id_field} is missing from the claimed public artifact")
    payload = dict(document)
    claimed = payload.pop(id_field)
    _cid(claimed, id_field)
    recomputed = _hash(domain, payload)
    if claimed != recomputed:
        _fail(f"{id_field} was not recomputed under its registered domain")
    return recomputed


def _module(name: str) -> Any:
    if (
        type(name) is not str
        or not name.startswith("acfqp.")
        or name.count(".") != 1
    ):
        _fail("semantic authority module name is malformed")
    return importlib.import_module(name)


class V075SemanticAuthorityRoleV1(str, Enum):
    PRIVATE_ENVIRONMENT_GENERATION_PROFILE = (
        "PRIVATE_ENVIRONMENT_GENERATION_PROFILE"
    )
    REGISTERED_OCCURRENCE_WORKER_REGISTRY = (
        "REGISTERED_OCCURRENCE_WORKER_REGISTRY"
    )
    ROUTE_NATIVE_BACKEND_RESULT = "ROUTE_NATIVE_BACKEND_RESULT"
    TOTAL_LIFT_RESULT = "TOTAL_LIFT_RESULT"
    CAMPAIGN_RECONCILIATION_READINESS = (
        "CAMPAIGN_RECONCILIATION_READINESS"
    )
    COMPLETE_BUNDLE_ENDPOINT_READINESS = (
        "COMPLETE_BUNDLE_ENDPOINT_READINESS"
    )


class V075ProductionReadinessBlockerV1(str, Enum):
    WORKER_REGISTRY_DRAFT_ONLY = "WORKER_REGISTRY_DRAFT_ONLY"
    ROUTE_NATIVE_BACKEND_NONAUTHORIZING = (
        "ROUTE_NATIVE_BACKEND_NONAUTHORIZING"
    )
    TOTAL_LIFT_EXECUTION_LOCKED = "TOTAL_LIFT_EXECUTION_LOCKED"
    BATCHED_OBSERVER_TOTAL_LIFT_LINEAGE_UNBOUND = (
        "BATCHED_OBSERVER_TOTAL_LIFT_LINEAGE_UNBOUND"
    )
    RECONCILIATION_PROTOCOL_NOT_READY = (
        "RECONCILIATION_PROTOCOL_NOT_READY"
    )
    COMPLETE_BUNDLE_ENDPOINT_NOT_READY = (
        "COMPLETE_BUNDLE_ENDPOINT_NOT_READY"
    )
    LEGACY_V072_RUNTIME_IN_PRODUCTION_DEPENDENCY_CLOSURE = (
        "LEGACY_V072_RUNTIME_IN_PRODUCTION_DEPENDENCY_CLOSURE"
    )
    TARGET_PROCESS_DEPENDENCY_BOUNDARY_VIOLATION = (
        "TARGET_PROCESS_DEPENDENCY_BOUNDARY_VIOLATION"
    )
    OFFICIAL_EXECUTION_LOCKED = "OFFICIAL_EXECUTION_LOCKED"
    WORKLOAD_ECONOMICS_GATE_NOT_RUN = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    COUNTER_COMPLETENESS_GATE_NOT_RUN = (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    CONSTRUCTION_SCOPE_ONLY = "CONSTRUCTION_SCOPE_ONLY"
    TOTAL_LIFT_NONPOSITIVE_OR_NONCERTIFICATE = (
        "TOTAL_LIFT_NONPOSITIVE_OR_NONCERTIFICATE"
    )


_OFFICIAL_ONLY_LOCKS = frozenset(
    {
        V075ProductionReadinessBlockerV1.OFFICIAL_EXECUTION_LOCKED,
        V075ProductionReadinessBlockerV1.WORKLOAD_ECONOMICS_GATE_NOT_RUN,
        V075ProductionReadinessBlockerV1.COUNTER_COMPLETENESS_GATE_NOT_RUN,
    }
)


@dataclass(frozen=True, slots=True)
class V075SemanticAuthorityRoleSpecV1:
    ordinal: int
    role: V075SemanticAuthorityRoleV1
    module_name: str
    artifact_schemas: tuple[str, ...]
    artifact_domains: tuple[str, ...]
    prerequisite_roles: tuple[V075SemanticAuthorityRoleV1, ...]
    public_context_binding: str
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal not in range(len(V075SemanticAuthorityRoleV1))
            or type(self.role) is not V075SemanticAuthorityRoleV1
            or type(self.module_name) is not str
            or not self.module_name.startswith("acfqp.v075_")
            or type(self.artifact_schemas) is not tuple
            or not self.artifact_schemas
            or len(set(self.artifact_schemas)) != len(self.artifact_schemas)
            or any(
                type(value) is not str
                or not value.startswith("acfqp.v075_")
                or not value.endswith(".v1")
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
                or not value.endswith(":v1")
                for value in self.artifact_domains
            )
            or type(self.prerequisite_roles) is not tuple
            or any(
                type(value) is not V075SemanticAuthorityRoleV1
                for value in self.prerequisite_roles
            )
            or len(set(self.prerequisite_roles))
            != len(self.prerequisite_roles)
            or type(self.public_context_binding) is not str
            or self.public_context_binding
            not in {
                "FAMILY",
                "NONE",
                "REQUEST_CONTEXT_AND_OCCURRENCE",
                "TYPED_OCCURRENCE_CONTEXT",
            }
        ):
            _fail("semantic role specification is malformed")
        object.__setattr__(
            self,
            "_spec_id",
            _registry_hash("role_spec", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_production_semantic_role_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "role": self.role.value,
            "module_name": self.module_name,
            "artifact_schemas": list(self.artifact_schemas),
            "artifact_domains": list(self.artifact_domains),
            "prerequisite_roles": [
                item.value for item in self.prerequisite_roles
            ],
            "public_context_binding": self.public_context_binding,
            "claimed_status_or_id_sufficient": False,
            "semantic_recomputation_required": True,
        }

    @property
    def spec_id(self) -> str:
        return self._spec_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "spec_id": self.spec_id}


_ROLE_ROWS = (
    (
        V075SemanticAuthorityRoleV1
        .PRIVATE_ENVIRONMENT_GENERATION_PROFILE,
        "acfqp.v075_private_environment_generation_profile_v1",
        ("acfqp.v075_private_environment_generation_profile.v1",),
        ("acfqp:v075-private-environment-generation-profile:v1",),
        (),
        "FAMILY",
    ),
    (
        V075SemanticAuthorityRoleV1
        .REGISTERED_OCCURRENCE_WORKER_REGISTRY,
        "acfqp.v075_registered_occurrence_worker_v1",
        ("acfqp.v075_production_worker_registry_draft.v1",),
        ("acfqp:v075-production-worker-registry-draft:v1",),
        (
            V075SemanticAuthorityRoleV1
            .PRIVATE_ENVIRONMENT_GENERATION_PROFILE,
        ),
        "NONE",
    ),
    (
        V075SemanticAuthorityRoleV1.ROUTE_NATIVE_BACKEND_RESULT,
        "acfqp.v075_route_native_backend_core_v1",
        ("acfqp.v075_route_native_backend_result.v1",),
        ("acfqp:v075-route-native-backend-result:v1",),
        (
            V075SemanticAuthorityRoleV1
            .REGISTERED_OCCURRENCE_WORKER_REGISTRY,
        ),
        "REQUEST_CONTEXT_AND_OCCURRENCE",
    ),
    (
        V075SemanticAuthorityRoleV1.TOTAL_LIFT_RESULT,
        "acfqp.v075_total_lift_authority_v1",
        (
            "acfqp.v075_total_lift_exact_endpoint.v1",
            "acfqp.v075_total_lift_statistical_envelope_miss.v1",
            "acfqp.v075_total_lift_protocol_failure.v1",
        ),
        (
            "acfqp:v075-total-lift-exact-endpoint:v1",
            "acfqp:v075-total-lift-statistical-envelope-miss:v1",
            "acfqp:v075-total-lift-protocol-failure:v1",
        ),
        (V075SemanticAuthorityRoleV1.ROUTE_NATIVE_BACKEND_RESULT,),
        "TYPED_OCCURRENCE_CONTEXT",
    ),
    (
        V075SemanticAuthorityRoleV1
        .CAMPAIGN_RECONCILIATION_READINESS,
        "acfqp.v075_campaign_reconciliation_v1",
        ("acfqp.v075_production_reconciliation_readiness.v1",),
        ("acfqp:v075-production-reconciliation-readiness:v1",),
        (
            V075SemanticAuthorityRoleV1
            .PRIVATE_ENVIRONMENT_GENERATION_PROFILE,
            V075SemanticAuthorityRoleV1
            .REGISTERED_OCCURRENCE_WORKER_REGISTRY,
            V075SemanticAuthorityRoleV1.ROUTE_NATIVE_BACKEND_RESULT,
            V075SemanticAuthorityRoleV1.TOTAL_LIFT_RESULT,
        ),
        "FAMILY",
    ),
    (
        V075SemanticAuthorityRoleV1
        .COMPLETE_BUNDLE_ENDPOINT_READINESS,
        "acfqp.v075_complete_bundle_endpoint_verifier_v1",
        (
            "acfqp.v075_production_complete_bundle_endpoint_readiness.v1",
        ),
        (
            "acfqp:v075-production-complete-bundle-endpoint-readiness:v1",
        ),
        (
            V075SemanticAuthorityRoleV1
            .CAMPAIGN_RECONCILIATION_READINESS,
        ),
        "FAMILY",
    ),
)


@dataclass(frozen=True, slots=True)
class V075ProductionSemanticAuthorityRegistryV1:
    role_specs: tuple[V075SemanticAuthorityRoleSpecV1, ...]
    _registry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        expected = tuple(
            V075SemanticAuthorityRoleSpecV1(index, *row)
            for index, row in enumerate(_ROLE_ROWS)
        )
        if self.role_specs != expected:
            _fail("semantic authority registry is incomplete or reordered")
        prior: set[V075SemanticAuthorityRoleV1] = set()
        domains: set[str] = set()
        schemas: set[str] = set()
        for spec in self.role_specs:
            if not set(spec.prerequisite_roles) <= prior:
                _fail("semantic authority role graph is cyclic or forward")
            if domains & set(spec.artifact_domains):
                _fail("semantic artifact domains overlap across roles")
            if schemas & set(spec.artifact_schemas):
                _fail("semantic artifact schemas overlap across roles")
            domains.update(spec.artifact_domains)
            schemas.update(spec.artifact_schemas)
            prior.add(spec.role)
        object.__setattr__(
            self,
            "_registry_id",
            _registry_hash("registry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_semantic_authority_registry.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "role_order": [item.role.value for item in self.role_specs],
            "role_spec_ids": [item.spec_id for item in self.role_specs],
            "role_count": len(self.role_specs),
            "status_strings_are_evidence": False,
            "claimed_content_ids_are_evidence": False,
            "independent_semantic_recomputation_required": True,
            "production_ready_claimed": False,
        }

    @property
    def registry_id(self) -> str:
        return self._registry_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "role_specs": [item.to_document() for item in self.role_specs],
            "registry_id": self.registry_id,
        }

    def require_role(
        self,
        role: V075SemanticAuthorityRoleV1,
    ) -> V075SemanticAuthorityRoleSpecV1:
        if type(role) is not V075SemanticAuthorityRoleV1:
            _fail("semantic authority role lookup is not typed")
        return self.role_specs[list(V075SemanticAuthorityRoleV1).index(role)]


def freeze_v075_production_semantic_authority_registry_v1(
) -> V075ProductionSemanticAuthorityRegistryV1:
    return V075ProductionSemanticAuthorityRegistryV1(
        tuple(
            V075SemanticAuthorityRoleSpecV1(index, *row)
            for index, row in enumerate(_ROLE_ROWS)
        )
    )


def _local_imports(module_basename: str) -> tuple[str, ...]:
    package_root = Path(__file__).resolve().parent
    path = package_root / f"{module_basename}.py"
    if not path.is_file():
        return ()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as error:
        raise V075ProductionSemanticAuthorityInvariantViolation(
            f"cannot inspect dependency source for {module_basename}: {error}"
        ) from error
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("acfqp."):
                    imports.add(alias.name.split(".", 1)[1].split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "acfqp":
                imports.update(alias.name for alias in node.names)
            elif node.module.startswith("acfqp."):
                imports.add(
                    node.module.split(".", 1)[1].split(".", 1)[0]
                )
    return tuple(sorted(imports))


_TARGET_PROCESS_ROLES = {
    V075SemanticAuthorityRoleV1.REGISTERED_OCCURRENCE_WORKER_REGISTRY,
    V075SemanticAuthorityRoleV1.ROUTE_NATIVE_BACKEND_RESULT,
}

_TARGET_PROCESS_FORBIDDEN_EXACT_MODULES = {
    "v075_private_environment_generation_profile_v1",
    "v075_private_observer_boundary_v1",
    "v075_source_offline_work_materializer_v1",
    "v075_source_prior_adapter_v1",
    "v075_frozen_source_proposal_archive_v1",
}


_DEPENDENCY_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075SemanticDependencyClosureV1:
    _issuer: object = field(repr=False, compare=False)
    role: V075SemanticAuthorityRoleV1
    root_module: str
    local_modules: tuple[str, ...]
    legacy_v072_modules: tuple[str, ...]
    target_process_forbidden_modules: tuple[str, ...]
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _DEPENDENCY_ISSUER
            or type(self.role) is not V075SemanticAuthorityRoleV1
            or type(self.root_module) is not str
            or not self.root_module.startswith("acfqp.")
            or self.local_modules
            != tuple(sorted(set(self.local_modules)))
            or self.legacy_v072_modules
            != tuple(sorted(set(self.legacy_v072_modules)))
            or self.target_process_forbidden_modules
            != tuple(sorted(set(self.target_process_forbidden_modules)))
            or not set(self.legacy_v072_modules) <= set(self.local_modules)
            or not set(self.target_process_forbidden_modules) <= set(
                self.local_modules
            )
        ):
            _fail("semantic dependency closure is malformed")
        object.__setattr__(
            self,
            "_closure_id",
            _registry_hash("dependency_closure", self._payload()),
        )

    @property
    def production_dependency_clean(self) -> bool:
        return not (
            self.legacy_v072_modules
            or self.target_process_forbidden_modules
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_semantic_dependency_closure.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "role": self.role.value,
            "root_module": self.root_module,
            "local_modules": list(self.local_modules),
            "legacy_v072_modules": list(self.legacy_v072_modules),
            "target_process_forbidden_modules": list(
                self.target_process_forbidden_modules
            ),
            "production_dependency_clean": (
                self.production_dependency_clean
            ),
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


def audit_v075_semantic_dependency_closure_v1(
    role: V075SemanticAuthorityRoleV1,
) -> V075SemanticDependencyClosureV1:
    registry = freeze_v075_production_semantic_authority_registry_v1()
    spec = registry.require_role(role)
    root = spec.module_name.split(".", 1)[1]
    pending = [root]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(
            value
            for value in _local_imports(current)
            if value not in seen
        )
    legacy = tuple(sorted(value for value in seen if value.startswith("v072_")))
    target_forbidden = (
        tuple(
            sorted(
                value
                for value in seen
                if value in _TARGET_PROCESS_FORBIDDEN_EXACT_MODULES
                or value.startswith("v072_")
            )
        )
        if role in _TARGET_PROCESS_ROLES
        else ()
    )
    return V075SemanticDependencyClosureV1(
        _DEPENDENCY_ISSUER,
        role,
        spec.module_name,
        tuple(sorted(seen)),
        legacy,
        target_forbidden,
    )


_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075SemanticArtifactVerificationV1:
    _issuer: object = field(repr=False, compare=False)
    role: V075SemanticAuthorityRoleV1
    artifact_schema: str
    artifact_id: str
    family_generation_id: str
    context_id: str | None
    occurrence_id: str | None
    bound_ids: tuple[tuple[str, str], ...]
    blockers: tuple[V075ProductionReadinessBlockerV1, ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        registry = freeze_v075_production_semantic_authority_registry_v1()
        spec = registry.require_role(self.role)
        _cid(self.artifact_id, "semantic artifact")
        _cid(self.family_generation_id, "semantic family generation")
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or self.artifact_schema not in spec.artifact_schemas
            or (
                self.context_id is not None
                and _cid(self.context_id, "semantic context")
                != self.context_id
            )
            or (
                self.occurrence_id is not None
                and _cid(self.occurrence_id, "semantic occurrence")
                != self.occurrence_id
            )
            or self.bound_ids != tuple(sorted(set(self.bound_ids)))
            or any(
                type(key) is not str
                or not key
                or type(value) is not str
                or _cid(value, f"semantic binding {key}") != value
                for key, value in self.bound_ids
            )
            or self.blockers != tuple(
                sorted(set(self.blockers), key=lambda item: item.value)
            )
            or any(
                type(item) is not V075ProductionReadinessBlockerV1
                for item in self.blockers
            )
        ):
            _fail("semantic artifact verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _registry_hash("verification", self._payload()),
        )

    @property
    def production_authorizing(self) -> bool:
        return not self.blockers

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_semantic_artifact_verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "semantic_registry_id": (
                freeze_v075_production_semantic_authority_registry_v1()
                .registry_id
            ),
            "role": self.role.value,
            "artifact_schema": self.artifact_schema,
            "artifact_id": self.artifact_id,
            "family_generation_id": self.family_generation_id,
            "context_id": self.context_id,
            "occurrence_id": self.occurrence_id,
            "bound_ids": [
                {"binding": key, "content_id": value}
                for key, value in self.bound_ids
            ],
            "semantic_recomputation_passed": True,
            "claimed_status_or_id_used_as_evidence": False,
            "blockers": [item.value for item in self.blockers],
            "production_authorizing": self.production_authorizing,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def _verification(
    *,
    role: V075SemanticAuthorityRoleV1,
    artifact_schema: str,
    artifact_id: str,
    context_id: str | None,
    occurrence_id: str | None,
    bound_ids: Mapping[str, str],
    blockers: tuple[V075ProductionReadinessBlockerV1, ...],
) -> V075SemanticArtifactVerificationV1:
    family = public_authority.freeze_v075_public_family_generation_v1()
    return V075SemanticArtifactVerificationV1(
        _VERIFICATION_ISSUER,
        role,
        artifact_schema,
        artifact_id,
        family.generation_id,
        context_id,
        occurrence_id,
        tuple(sorted(bound_ids.items())),
        tuple(sorted(set(blockers), key=lambda item: item.value)),
    )


def verify_v075_private_generation_profile_artifact_v1(
    artifact_bytes: bytes,
) -> V075SemanticArtifactVerificationV1:
    role = (
        V075SemanticAuthorityRoleV1
        .PRIVATE_ENVIRONMENT_GENERATION_PROFILE
    )
    spec = (
        freeze_v075_production_semantic_authority_registry_v1()
        .require_role(role)
    )
    component = _module(spec.module_name)
    claimed = _canonical_document(
        artifact_bytes,
        field_name="private generation profile",
    )
    expected = (
        component.freeze_v075_private_environment_generation_profile_v1()
        .to_document()
    )
    if canonical_json_bytes(claimed) != canonical_json_bytes(expected):
        _fail("private generation profile differs from exact public replay")
    artifact_id = _recompute_document_id(
        claimed,
        domain=spec.artifact_domains[0],
        id_field="profile_id",
    )
    family = public_authority.freeze_v075_public_family_generation_v1()
    if (
        claimed["family_generation_id"] != family.generation_id
        or claimed["context_ids_in_generation_order"]
        != [item.context_id for item in family.replicate_contexts]
        or claimed["context_ordinals"] != [0, 1, 2]
        or claimed["selected_law_serialized"] is not False
        or claimed["target_execution_allowed"] is not False
    ):
        _fail("private generation profile family/privacy binding changed")
    return _verification(
        role=role,
        artifact_schema=claimed["schema"],
        artifact_id=artifact_id,
        context_id=None,
        occurrence_id=None,
        bound_ids={"PUBLIC_FAMILY_GENERATION": family.generation_id},
        blockers=(
            V075ProductionReadinessBlockerV1.OFFICIAL_EXECUTION_LOCKED,
        ),
    )


def verify_v075_worker_registry_artifact_v1(
    artifact_bytes: bytes,
) -> V075SemanticArtifactVerificationV1:
    role = (
        V075SemanticAuthorityRoleV1
        .REGISTERED_OCCURRENCE_WORKER_REGISTRY
    )
    spec = (
        freeze_v075_production_semantic_authority_registry_v1()
        .require_role(role)
    )
    component = _module(spec.module_name)
    claimed = _canonical_document(
        artifact_bytes,
        field_name="occurrence worker registry",
    )
    expected = component.freeze_v075_worker_registry_draft_v1().to_document()
    if claimed != expected:
        _fail("occurrence worker registry differs from exact replay")
    registrations = claimed.get("registrations")
    if type(registrations) is not list or len(registrations) != 5:
        _fail("occurrence worker registry does not contain all five arms")
    for registration in registrations:
        _recompute_document_id(
            registration,
            domain=component.DOMAIN_TAGS["arm_registration"],
            id_field="registration_id",
        )
        if (
            registration["backend_status"] != "NOT_READY"
            or registration["total_lift_authority_required"] is not True
            or registration["v072_target_authority_allowed"] is not False
        ):
            _fail("worker arm registration is not fail-closed")
    artifact_id = _recompute_document_id(
        {
            key: value
            for key, value in claimed.items()
            if key != "registrations"
        },
        domain=spec.artifact_domains[0],
        id_field="registry_id",
    )
    if (
        claimed["registration_ids"]
        != [item["registration_id"] for item in registrations]
        or claimed["final_spec_frozen"] is not False
        or claimed["construction_fixture_only"] is not True
    ):
        _fail("worker registry nested identities or readiness changed")
    return _verification(
        role=role,
        artifact_schema=claimed["schema"],
        artifact_id=artifact_id,
        context_id=None,
        occurrence_id=None,
        bound_ids={},
        blockers=(
            V075ProductionReadinessBlockerV1.WORKER_REGISTRY_DRAFT_ONLY,
        ),
    )


def _registered_context_id(context_id: str) -> str:
    _cid(context_id, "expected public context")
    family = public_authority.freeze_v075_public_family_generation_v1()
    if context_id not in {
        item.context_id for item in family.replicate_contexts
    }:
        _fail("artifact context is outside the preregistered public family")
    return context_id


def verify_v075_route_native_backend_artifact_v1(
    *,
    request_bytes: bytes,
    result_bytes: bytes,
    expected_target_tape_namespace_id: str,
    expected_context_id: str,
    expected_occurrence_id: str,
    expected_arm: str,
) -> V075SemanticArtifactVerificationV1:
    role = V075SemanticAuthorityRoleV1.ROUTE_NATIVE_BACKEND_RESULT
    spec = (
        freeze_v075_production_semantic_authority_registry_v1()
        .require_role(role)
    )
    worker = _module(
        "acfqp.v075_registered_occurrence_worker_v1"
    )
    backend = _module(spec.module_name)
    request = worker.load_v075_registered_occurrence_worker_request_v1(
        request_bytes
    )
    result = backend.verify_v075_route_native_backend_result_v1(
        request_bytes=request_bytes,
        claimed_bytes=result_bytes,
    )
    claimed = _canonical_document(
        result_bytes,
        field_name="route-native backend result",
    )
    _cid(
        expected_target_tape_namespace_id,
        "expected target-tape namespace",
    )
    _registered_context_id(expected_context_id)
    _cid(expected_occurrence_id, "expected occurrence")
    if (
        type(expected_arm) is not str
        or request["target_tape_namespace_id"]
        != expected_target_tape_namespace_id
        or request["context_id"] != expected_context_id
        or request["occurrence_id"] != expected_occurrence_id
        or request["arm"] != expected_arm
        or claimed["request_id"] != request["request_id"]
        or claimed["occurrence_id"] != request["occurrence_id"]
        or claimed["arm"] != request["arm"]
        or claimed["production_backend_ready"] is not False
        or claimed["scientific_result"] is not False
        or result.total_lift_input.to_document()[
            "ready_for_total_lift_evaluation"
        ]
        is not False
    ):
        _fail("route-native result escaped its exact request binding")
    summary = {
        key: value
        for key, value in claimed.items()
        if key
        not in {
            "schedule",
            "proposal",
            "model",
            "policy",
            "envelope",
            "total_lift_input",
            "work",
        }
    }
    artifact_id = _recompute_document_id(
        summary,
        domain=spec.artifact_domains[0],
        id_field="result_id",
    )
    return _verification(
        role=role,
        artifact_schema=claimed["schema"],
        artifact_id=artifact_id,
        context_id=expected_context_id,
        occurrence_id=expected_occurrence_id,
        bound_ids={
            "TARGET_TAPE_NAMESPACE": expected_target_tape_namespace_id,
            "WORKER_REGISTRY": request["worker_registry_id"],
            "WORKER_REQUEST": request["request_id"],
        },
        blockers=(
            V075ProductionReadinessBlockerV1
            .ROUTE_NATIVE_BACKEND_NONAUTHORIZING,
        ),
    )


def verify_v075_total_lift_artifact_v1(
    *,
    envelope: Any,
    exact_replay: Any,
    claimed_outcome: Any,
    expected_target_tape_namespace_id: str,
    expected_context_id: str,
    expected_occurrence_id: str,
) -> V075SemanticArtifactVerificationV1:
    role = V075SemanticAuthorityRoleV1.TOTAL_LIFT_RESULT
    spec = (
        freeze_v075_production_semantic_authority_registry_v1()
        .require_role(role)
    )
    lift = _module(spec.module_name)
    expected = lift.evaluate_total_lift_v1(
        envelope=envelope,
        exact_replay=exact_replay,
    )
    allowed_types = (
        lift.V075TotalLiftEndpointV1,
        lift.V075TotalLiftStatisticalEnvelopeMissV1,
        lift.V075TotalLiftProtocolFailureV1,
    )
    if (
        type(claimed_outcome) not in allowed_types
        or type(expected) is not type(claimed_outcome)
        or expected.to_document() != claimed_outcome.to_document()
    ):
        _fail("total-lift result differs from independent exact replay")
    occurrence = exact_replay.occurrence
    _cid(
        expected_target_tape_namespace_id,
        "expected target-tape namespace",
    )
    _registered_context_id(expected_context_id)
    _cid(expected_occurrence_id, "expected occurrence")
    if (
        occurrence.namespace.target_tape_namespace_id
        != expected_target_tape_namespace_id
        or occurrence.context.context_id != expected_context_id
        or occurrence.occurrence_id != expected_occurrence_id
        or envelope.policy.model.occurrence != occurrence
    ):
        _fail("total-lift result was transplanted across occurrence/context")
    document = claimed_outcome.to_document()
    schema = document.get("schema")
    if schema not in spec.artifact_schemas:
        _fail("total-lift result schema is not registered for its role")
    index = spec.artifact_schemas.index(schema)
    id_field = (
        "endpoint_id"
        if type(claimed_outcome) is lift.V075TotalLiftEndpointV1
        else (
            "miss_id"
            if type(claimed_outcome)
            is lift.V075TotalLiftStatisticalEnvelopeMissV1
            else "failure_id"
        )
    )
    artifact_id = _recompute_document_id(
        document,
        domain=spec.artifact_domains[index],
        id_field=id_field,
    )
    blockers = {
        V075ProductionReadinessBlockerV1.TOTAL_LIFT_EXECUTION_LOCKED,
    }
    if (
        exact_replay.scope.value != "INDEPENDENT_CLOSURE_REPLAY"
        or exact_replay.bound_model_id is None
        or exact_replay.bound_policy_id is None
        or exact_replay.bound_envelope_id is None
        or exact_replay.replay_request_cas_id is None
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1.CONSTRUCTION_SCOPE_ONLY
        )
    if (
        type(claimed_outcome) is not lift.V075TotalLiftEndpointV1
        or claimed_outcome.status
        is not lift.V075TotalLiftEndpointStatusV1.EXACT_POSITIVE_ENDPOINT
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1
            .TOTAL_LIFT_NONPOSITIVE_OR_NONCERTIFICATE
        )
    return _verification(
        role=role,
        artifact_schema=schema,
        artifact_id=artifact_id,
        context_id=expected_context_id,
        occurrence_id=expected_occurrence_id,
        bound_ids={
            "EXACT_REPLAY_BOUNDARY": exact_replay.boundary_id,
            "OPERATIONAL_ENVELOPE": envelope.envelope_id,
            "TARGET_TAPE_NAMESPACE": expected_target_tape_namespace_id,
        },
        blockers=tuple(blockers),
    )


def _verify_readiness_artifact(
    *,
    role: V075SemanticAuthorityRoleV1,
    artifact_bytes: bytes,
) -> V075SemanticArtifactVerificationV1:
    spec = (
        freeze_v075_production_semantic_authority_registry_v1()
        .require_role(role)
    )
    component = _module(spec.module_name)
    if (
        role
        is V075SemanticAuthorityRoleV1
        .CAMPAIGN_RECONCILIATION_READINESS
    ):
        expected_object = (
            component.v075_production_reconciliation_readiness_v1()
        )
        blocker = (
            V075ProductionReadinessBlockerV1
            .RECONCILIATION_PROTOCOL_NOT_READY
        )
        try:
            component.reconcile_v075_campaign_v1()
        except component.V075ProductionReconciliationNotReady:
            pass
        else:
            _fail("reconciliation readiness artifact contradicts execution")
    elif (
        role
        is V075SemanticAuthorityRoleV1
        .COMPLETE_BUNDLE_ENDPOINT_READINESS
    ):
        expected_object = (
            component
            .v075_production_complete_bundle_endpoint_readiness_v1()
        )
        blocker = (
            V075ProductionReadinessBlockerV1
            .COMPLETE_BUNDLE_ENDPOINT_NOT_READY
        )
        try:
            component.verify_v075_complete_bundle_endpoint_v1()
        except component.V075ProductionCompleteBundleEndpointNotReady:
            pass
        else:
            _fail("endpoint readiness artifact contradicts execution")
    else:  # pragma: no cover - internal role dispatch is frozen
        raise RuntimeError("readiness verifier received a non-readiness role")
    claimed = _canonical_document(
        artifact_bytes,
        field_name=f"{role.value} artifact",
    )
    expected = expected_object.to_document()
    if claimed != expected:
        _fail("readiness artifact differs from executable semantic replay")
    artifact_id = _recompute_document_id(
        claimed,
        domain=spec.artifact_domains[0],
        id_field="status_id",
    )
    if (
        claimed["official_execution_allowed"] is not False
        or claimed["official_scalar_cost"] is not None
        or claimed["official_N_break_even"] is not None
        or claimed["workload_economics_gate_status"] != "NOT_RUN"
        or claimed["counter_completeness_gate_status"] != "NOT_RUN"
    ):
        _fail("readiness artifact illegally opened official gates")
    family = public_authority.freeze_v075_public_family_generation_v1()
    closure = audit_v075_semantic_dependency_closure_v1(role)
    blockers = {
        blocker,
        V075ProductionReadinessBlockerV1.OFFICIAL_EXECUTION_LOCKED,
        V075ProductionReadinessBlockerV1
        .WORKLOAD_ECONOMICS_GATE_NOT_RUN,
        V075ProductionReadinessBlockerV1
        .COUNTER_COMPLETENESS_GATE_NOT_RUN,
    }
    if closure.legacy_v072_modules:
        blockers.add(
            V075ProductionReadinessBlockerV1
            .LEGACY_V072_RUNTIME_IN_PRODUCTION_DEPENDENCY_CLOSURE
        )
    return _verification(
        role=role,
        artifact_schema=claimed["schema"],
        artifact_id=artifact_id,
        context_id=None,
        occurrence_id=None,
        bound_ids={
            "DEPENDENCY_CLOSURE": closure.closure_id,
            "PUBLIC_FAMILY_GENERATION": family.generation_id,
        },
        blockers=tuple(blockers),
    )


def verify_v075_reconciliation_readiness_artifact_v1(
    artifact_bytes: bytes,
) -> V075SemanticArtifactVerificationV1:
    return _verify_readiness_artifact(
        role=(
            V075SemanticAuthorityRoleV1
            .CAMPAIGN_RECONCILIATION_READINESS
        ),
        artifact_bytes=artifact_bytes,
    )


def verify_v075_complete_bundle_readiness_artifact_v1(
    artifact_bytes: bytes,
) -> V075SemanticArtifactVerificationV1:
    return _verify_readiness_artifact(
        role=(
            V075SemanticAuthorityRoleV1
            .COMPLETE_BUNDLE_ENDPOINT_READINESS
        ),
        artifact_bytes=artifact_bytes,
    )


_READINESS_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075ProductionSemanticReadinessAuditV1:
    _issuer: object = field(repr=False, compare=False)
    semantic_registry_id: str
    dependency_closures: tuple[V075SemanticDependencyClosureV1, ...]
    blockers: tuple[V075ProductionReadinessBlockerV1, ...]
    _audit_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        registry = freeze_v075_production_semantic_authority_registry_v1()
        if (
            self._issuer is not _READINESS_ISSUER
            or self.semantic_registry_id != registry.registry_id
            or tuple(item.role for item in self.dependency_closures)
            != tuple(V075SemanticAuthorityRoleV1)
            or any(
                type(item) is not V075SemanticDependencyClosureV1
                for item in self.dependency_closures
            )
            or self.blockers != tuple(
                sorted(set(self.blockers), key=lambda item: item.value)
            )
            or any(
                type(item) is not V075ProductionReadinessBlockerV1
                for item in self.blockers
            )
        ):
            _fail("production semantic readiness audit is malformed")
        object.__setattr__(
            self,
            "_audit_id",
            _registry_hash("readiness", self._payload()),
        )

    @property
    def registered_target_ready(self) -> bool:
        """Whether the fresh preregistered scientific campaign may run."""

        return not any(
            blocker not in _OFFICIAL_ONLY_LOCKS
            for blocker in self.blockers
        )

    @property
    def official_economics_ready(self) -> bool:
        return self.registered_target_ready and not any(
            blocker in _OFFICIAL_ONLY_LOCKS
            for blocker in self.blockers
        )

    @property
    def production_ready(self) -> bool:
        """Compatibility alias for registered target execution readiness."""

        return self.registered_target_ready

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_production_semantic_readiness_audit.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "semantic_registry_id": self.semantic_registry_id,
            "dependency_closure_ids": [
                item.closure_id for item in self.dependency_closures
            ],
            "blockers": [item.value for item in self.blockers],
            "production_ready": self.production_ready,
            "registered_target_ready": self.registered_target_ready,
            "official_economics_ready": self.official_economics_ready,
            "committed_artifact_path_replay_implemented": (
                COMMITTED_ARTIFACT_PATH_REPLAY_IMPLEMENTED
            ),
            "claimed_status_strings_accepted": False,
            "claimed_content_ids_accepted_without_replay": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def audit_id(self) -> str:
        return self._audit_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "dependency_closures": [
                item.to_document() for item in self.dependency_closures
            ],
            "audit_id": self.audit_id,
        }


def audit_v075_production_semantic_readiness_v1(
) -> V075ProductionSemanticReadinessAuditV1:
    registry = freeze_v075_production_semantic_authority_registry_v1()
    closures = tuple(
        audit_v075_semantic_dependency_closure_v1(role)
        for role in V075SemanticAuthorityRoleV1
    )
    blockers: set[V075ProductionReadinessBlockerV1] = set()

    private_profile = _module(
        "acfqp.v075_private_environment_generation_profile_v1"
    )
    worker = _module("acfqp.v075_registered_occurrence_worker_v1")
    backend = _module("acfqp.v075_route_native_backend_core_v1")
    lift = _module("acfqp.v075_total_lift_authority_v1")
    batched_observer = _module(
        "acfqp.v075_batched_observer_authority_v1"
    )
    reconciliation = _module("acfqp.v075_campaign_reconciliation_v1")
    endpoint = _module(
        "acfqp.v075_complete_bundle_endpoint_verifier_v1"
    )

    profile = (
        private_profile
        .freeze_v075_private_environment_generation_profile_v1()
    )
    if (
        profile.to_document()["target_execution_allowed"] is False
        or private_profile.TARGET_EXECUTION_ALLOWED is False
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1.OFFICIAL_EXECUTION_LOCKED
        )
    registry_draft = worker.freeze_v075_worker_registry_draft_v1()
    if (
        registry_draft.to_document()["final_spec_frozen"] is False
        or registry_draft.to_document()["construction_fixture_only"] is True
        or any(
            item.backend_status.value == "NOT_READY"
            for item in registry_draft.registrations
        )
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1.WORKER_REGISTRY_DRAFT_ONLY
        )
    if (
        backend.PRODUCTION_BACKEND_READY is False
        or all(
            item.value.startswith("NOT_READY_")
            for item in backend.V075BackendCandidateStatusV1
        )
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1
            .ROUTE_NATIVE_BACKEND_NONAUTHORIZING
        )
    if lift.PRODUCTION_TOTAL_LIFT_EXECUTION_ALLOWED is False:
        blockers.add(
            V075ProductionReadinessBlockerV1.TOTAL_LIFT_EXECUTION_LOCKED
        )
    mint_signature = inspect.signature(
        lift.verify_and_mint_production_exact_replay_boundary_v1
    )
    closure_annotation = str(
        mint_signature.parameters["observer_journal_closure"].annotation
    )
    batched_names = {
        name
        for name in dir(batched_observer)
        if "Batched" in name or "batched" in name
    }
    lift_batch_adapters = {
        name
        for name in dir(lift)
        if "batch" in name.lower()
        and ("mint" in name.lower() or "closure" in name.lower())
    }
    if (
        "V075ObserverJournalClosureV1" in closure_annotation
        and batched_names
        and not lift_batch_adapters
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1
            .BATCHED_OBSERVER_TOTAL_LIFT_LINEAGE_UNBOUND
        )

    reconciliation_readiness = (
        reconciliation.v075_production_reconciliation_readiness_v1()
        .to_document()
    )
    try:
        reconciliation.reconcile_v075_campaign_v1()
    except reconciliation.V075ProductionReconciliationNotReady:
        blockers.add(
            V075ProductionReadinessBlockerV1
            .RECONCILIATION_PROTOCOL_NOT_READY
        )
    else:
        if reconciliation_readiness["production_reconciliation_allowed"] is False:
            _fail("reconciliation status and executable API disagree")

    endpoint_readiness = (
        endpoint
        .v075_production_complete_bundle_endpoint_readiness_v1()
        .to_document()
    )
    try:
        endpoint.verify_v075_complete_bundle_endpoint_v1()
    except endpoint.V075ProductionCompleteBundleEndpointNotReady:
        blockers.add(
            V075ProductionReadinessBlockerV1
            .COMPLETE_BUNDLE_ENDPOINT_NOT_READY
        )
    else:
        if endpoint_readiness[
            "production_endpoint_verification_allowed"
        ] is False:
            _fail("endpoint status and executable API disagree")

    if any(item.legacy_v072_modules for item in closures):
        blockers.add(
            V075ProductionReadinessBlockerV1
            .LEGACY_V072_RUNTIME_IN_PRODUCTION_DEPENDENCY_CLOSURE
        )
    if any(
        item.target_process_forbidden_modules
        for item in closures
        if item.role in _TARGET_PROCESS_ROLES
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1
            .TARGET_PROCESS_DEPENDENCY_BOUNDARY_VIOLATION
        )
    if (
        reconciliation_readiness["official_execution_allowed"] is False
        or endpoint_readiness["official_execution_allowed"] is False
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1.OFFICIAL_EXECUTION_LOCKED
        )
    if (
        reconciliation_readiness["workload_economics_gate_status"]
        == "NOT_RUN"
        or endpoint_readiness["workload_economics_gate_status"] == "NOT_RUN"
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1
            .WORKLOAD_ECONOMICS_GATE_NOT_RUN
        )
    if (
        reconciliation_readiness["counter_completeness_gate_status"]
        == "NOT_RUN"
        or endpoint_readiness["counter_completeness_gate_status"] == "NOT_RUN"
    ):
        blockers.add(
            V075ProductionReadinessBlockerV1
            .COUNTER_COMPLETENESS_GATE_NOT_RUN
        )

    return V075ProductionSemanticReadinessAuditV1(
        _READINESS_ISSUER,
        registry.registry_id,
        closures,
        tuple(sorted(blockers, key=lambda item: item.value)),
    )


def require_v075_production_semantic_readiness_v1(
) -> V075ProductionSemanticReadinessAuditV1:
    audit = audit_v075_production_semantic_readiness_v1()
    if not audit.registered_target_ready:
        raise V075ProductionSemanticAuthorityNotReady(
            ",".join(
                item.value
                for item in audit.blockers
                if item not in _OFFICIAL_ONLY_LOCKS
            )
        )
    return audit


__all__ = [
    "COMMITTED_ARTIFACT_PATH_REPLAY_IMPLEMENTED",
    "DOMAIN_TAGS",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "V075ProductionReadinessBlockerV1",
    "V075ProductionSemanticAuthorityInvariantViolation",
    "V075ProductionSemanticAuthorityNotReady",
    "V075ProductionSemanticAuthorityRegistryV1",
    "V075ProductionSemanticReadinessAuditV1",
    "V075SemanticArtifactVerificationV1",
    "V075SemanticAuthorityRoleSpecV1",
    "V075SemanticAuthorityRoleV1",
    "V075SemanticDependencyClosureV1",
    "audit_v075_production_semantic_readiness_v1",
    "audit_v075_semantic_dependency_closure_v1",
    "freeze_v075_production_semantic_authority_registry_v1",
    "require_v075_production_semantic_readiness_v1",
    "verify_v075_complete_bundle_readiness_artifact_v1",
    "verify_v075_private_generation_profile_artifact_v1",
    "verify_v075_reconciliation_readiness_artifact_v1",
    "verify_v075_route_native_backend_artifact_v1",
    "verify_v075_total_lift_artifact_v1",
    "verify_v075_worker_registry_artifact_v1",
]
