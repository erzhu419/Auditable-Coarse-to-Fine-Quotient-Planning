"""Construction-only H1 direct-fallback two-role execution recipe.

This module closes a planning boundary, not an execution boundary.  It binds
a content-addressed claim in the canonical legacy H1 preexecution-candidate
schema and its
embedded frozen FALLBACK chain to the two-role successor requirements, the nine
shared-source manifest, a post-decision order, and the memory/output operands
that a future V7 authority must provide.

The preexecution replay here is deliberately bytes-only.  It checks canonical
content IDs and the typed route chain without calling ``kernel.step`` or the
fallback solver.  Consequently it is not a production current-identity
verifier.  In particular, the existing current-identity builder is forbidden
at preselection because it replays ground transitions.  No current root-cap
role-manifest/runtime instance is accepted as an H1 adapter.

All numeric shared-resource operands remain absent.  The recipe cannot issue a
route upper, route decision, receipt, CounterRecord, vector, terminal, or Gate.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import hmac
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_direct_fallback_shared_source_manifest_v1 as source_v1
from acfqp import construction_output_bytes_fixed_point_v1 as output_fixed_v1
from acfqp import v075_k7_production_broker_runtime_v2 as runtime_v2
from acfqp import v075_k7_production_role_manifest_v2 as role_manifest_v2
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CURRENT_IDENTITY_V1_DOMAIN,
    CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.routing_v1 import (
    DecisionPointV1,
    MarginalRouteDecisionV1,
    RouteDecisionContextV1,
    RouteKind,
    RouteSelection,
    RouteUpperBoundEnvelopeV1,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.50"
PROFILE_KEY = "construction_k7_h1_direct_fallback_two_role_recipe_v1"

CONSTRUCTION_ONLY = True
OFFICIAL_EXECUTION_ALLOWED = False
NUMERIC_AGGREGATE_CANDIDATE_ISSUED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
PRODUCTION_H1_BUSINESS_ADAPTER_PRESENT = False
PRODUCTION_CURRENT_IDENTITY_VERIFIER_PRESENT = False

PROFILE_DOMAIN = (
    CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_PROFILE_V1_DOMAIN
)
RECIPE_DOMAIN = CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_V1_DOMAIN
REQUESTED_PHASE3E_DOMAIN_TAGS = (PROFILE_DOMAIN, RECIPE_DOMAIN)
if not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("H1 two-role recipe domains are not centrally registered")

_PROFILE_ISSUER = object()
_RECIPE_ISSUER = object()
_LIVE_RECIPES: dict[int, tuple["H1DirectFallbackTwoRoleRecipeV1", bytes]] = {}

_PREEXECUTION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "durable_proof_id",
        "current_identity_attestation",
        "cardinality_source_id",
        "route_context",
        "decision_point",
        "cap_profile",
        "cardinality_bound",
        "cardinality",
        "route_upper_formula",
        "route_upper",
        "route_upper_derivation_proof",
        "route_decision",
        "current_identity_attestation_id",
        "current_identity_supplied_separately",
        "claimant_self_match_used",
        "cardinality_source_replayed_from_durable_h1_action_closure",
        "route_upper_arithmetic_replayed",
        "route_decision_frozen_before_kernel_access",
        "selected_route",
        "scope",
        "production_route_authority",
        "production_authorized",
        "existing_contract_1_semantic_registry_extended",
        "central_domain_registration_pending",
        "official_execution_allowed",
        "direct_fallback_preexecution_candidate_id",
    }
)
_CURRENT_IDENTITY_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "identity",
        "current_source_proof_sha256",
        "live_initial_law_id",
        "live_transition_law_id",
        "current_identity_source_supplied_separately_from_claimant",
        "claimant_identity_used_as_current_by_default",
        "live_kernel_and_query_replayed",
        "explicit_current_identity_components_required",
        "build_lane",
        "charged_as_operational_route_work",
        "central_domain_registration_pending",
        "production_authority",
        "current_identity_attestation_id",
    }
)


class ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error(ValueError):
    """The H1 source projection or construction recipe is malformed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _verify_embedded_id(
    document: Mapping[str, Any], *, id_field: str, domain: str, label: str
) -> str:
    if type(document) is not dict or id_field not in document:
        _fail(f"{label} lacks its content identity")
    identifier = _cid(document[id_field], label)
    payload = dict(document)
    payload.pop(id_field)
    if not hmac.compare_digest(content_id(domain, payload), identifier):
        _fail(f"{label} content identity is invalid")
    return identifier


class RecipeBlockerV1(str, Enum):
    PRODUCTION_CURRENT_IDENTITY_VERIFIER_MISSING = (
        "PRODUCTION_CURRENT_IDENTITY_VERIFIER_MISSING"
    )
    H1_BUSINESS_ADAPTER_MISSING = "H1_BUSINESS_ADAPTER_MISSING"
    PRODUCTION_MANIFEST_RUNTIME_INSTANCE_UNBOUND = (
        "PRODUCTION_MANIFEST_RUNTIME_INSTANCE_UNBOUND"
    )
    H1_ROLE_MANIFEST_AND_RUNTIME_PROFILES_MISSING = (
        "H1_ROLE_MANIFEST_AND_RUNTIME_PROFILES_MISSING"
    )
    BROKER_PARENT_CONTINUOUS_MEMORY_SCOPE_UNRESOLVED = (
        "BROKER_PARENT_CONTINUOUS_MEMORY_SCOPE_UNRESOLVED"
    )
    ROLE_MEMORY_MAX_OPERAND_AUTHORITIES_MISSING = (
        "ROLE_MEMORY_MAX_OPERAND_AUTHORITIES_MISSING"
    )
    OUTPUT_RENDERER_AND_FAILURE_BRANCH_AUTHORITIES_MISSING = (
        "OUTPUT_RENDERER_AND_FAILURE_BRANCH_AUTHORITIES_MISSING"
    )
    OUTPUT_BRANCH_PRESENCE_MATRIX_AUTHORITY_MISSING = (
        "OUTPUT_BRANCH_PRESENCE_MATRIX_AUTHORITY_MISSING"
    )
    READ_STAGE_MOUNT_CATALOGUES_MISSING = (
        "READ_STAGE_MOUNT_CATALOGUES_MISSING"
    )
    FORMAL_V7_ROUTE_DECISION_AUTHORITY_MISSING = (
        "FORMAL_V7_ROUTE_DECISION_AUTHORITY_MISSING"
    )


BLOCKERS = tuple(item.value for item in RecipeBlockerV1)


class BindingStatusV1(str, Enum):
    EXACT_PROFILE_BOUND_INSTANCE_REQUIRED = "EXACT_PROFILE_BOUND_INSTANCE_REQUIRED"
    REQUIRED_UNBOUND = "REQUIRED_UNBOUND"
    STRUCTURAL_BYTES_ONLY_NOT_SEMANTIC_AUTHORITY = (
        "STRUCTURAL_BYTES_ONLY_NOT_SEMANTIC_AUTHORITY"
    )


class MemoryScopeStatusV1(str, Enum):
    UNRESOLVED = "UNRESOLVED"


class BusinessResultPresenceV1(str, Enum):
    REQUIRED = "REQUIRED"
    TYPED_ABSENT_REQUIRED = "TYPED_ABSENT_REQUIRED"
    PHASE_SPLIT_REQUIRED = "PHASE_SPLIT_REQUIRED"


@dataclass(frozen=True, slots=True)
class PostDecisionStepV1:
    ordinal: int
    step_key: str
    owner_scope: str
    obligation: str

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal <= 0
            or type(self.step_key) is not str
            or not self.step_key
            or type(self.owner_scope) is not str
            or not self.owner_scope
            or type(self.obligation) is not str
            or not self.obligation
        ):
            _fail("post-decision step is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "step_key": self.step_key,
            "owner_scope": self.owner_scope,
            "obligation": self.obligation,
        }


@dataclass(frozen=True, slots=True)
class MemoryScopeRequirementV1:
    scope_key: str
    members: tuple[str, ...]
    cap_operand_role: str
    required_evidence: tuple[str, ...]
    numeric_cap_bytes: None = None

    def __post_init__(self) -> None:
        if (
            type(self.scope_key) is not str
            or not self.scope_key
            or type(self.members) is not tuple
            or not self.members
            or len(set(self.members)) != len(self.members)
            or any(type(item) is not str or not item for item in self.members)
            or type(self.cap_operand_role) is not str
            or not self.cap_operand_role
            or type(self.required_evidence) is not tuple
            or not self.required_evidence
            or len(set(self.required_evidence)) != len(self.required_evidence)
            or self.numeric_cap_bytes is not None
        ):
            _fail("memory-scope requirement is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "scope_key": self.scope_key,
            "members": list(self.members),
            "cap_operand_role": self.cap_operand_role,
            "required_evidence": list(self.required_evidence),
            "numeric_cap_bytes": None,
            "operand_authority_status": BindingStatusV1.REQUIRED_UNBOUND.value,
        }


@dataclass(frozen=True, slots=True)
class OutputRoleRequirementV1:
    role: str
    owner_scope: str
    durable_timing: str
    required_semantics: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            self.role not in output_fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
            or type(self.owner_scope) is not str
            or not self.owner_scope
            or type(self.durable_timing) is not str
            or not self.durable_timing
            or type(self.required_semantics) is not tuple
            or not self.required_semantics
            or len(set(self.required_semantics)) != len(self.required_semantics)
        ):
            _fail("output-role requirement is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "artifact_role": self.role,
            "owner_scope": self.owner_scope,
            "durable_timing": self.durable_timing,
            "required_semantics": list(self.required_semantics),
            "renderer_authority_status": BindingStatusV1.REQUIRED_UNBOUND.value,
        }


@dataclass(frozen=True, slots=True)
class FailureBranchRequirementV1:
    branch_key: str
    terminal_class: str
    terminal_code: str
    business_result_presence: BusinessResultPresenceV1
    durable_role_presence_rule: str
    required_preservation: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.branch_key) is not str
            or not self.branch_key
            or type(self.terminal_class) is not str
            or not self.terminal_class
            or type(self.terminal_code) is not str
            or not self.terminal_code
            or type(self.business_result_presence) is not BusinessResultPresenceV1
            or type(self.durable_role_presence_rule) is not str
            or not self.durable_role_presence_rule
            or type(self.required_preservation) is not tuple
            or not self.required_preservation
        ):
            _fail("failure-branch requirement is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "branch_key": self.branch_key,
            "terminal_class": self.terminal_class,
            "terminal_code": self.terminal_code,
            "business_result_presence": self.business_result_presence.value,
            "durable_role_presence_rule": self.durable_role_presence_rule,
            "required_preservation": list(self.required_preservation),
            "renderer_schema_authority_id": None,
            "branch_upper_operand_authority_id": None,
            "authority_status": BindingStatusV1.REQUIRED_UNBOUND.value,
        }


def _post_decision_steps() -> tuple[PostDecisionStepV1, ...]:
    rows = (
        (
            "assert_formal_route_decision",
            "BROKER_PARENT",
            "require a future formal V7 FALLBACK decision bound to this exact H1 identity before every execution-side access",
        ),
        (
            "open_complete_route_window",
            "BROKER_PARENT",
            "open one monotone accounting/access window; all nine shared paths remain inside it through final readback and cleanup",
        ),
        (
            "activate_frozen_broker_parent_memory_scope",
            "BROKER_PARENT",
            "replay the already frozen predecision broker-scope authority and activate continuous cap/peak coverage; resolving scope after route selection is forbidden",
        ),
        (
            "bind_outer_broker_worker_business_caps",
            "BROKER_PARENT",
            "bind and replay exact OUTER, BROKER_PARENT, WORKER and BUSINESS memory.max operands before launch; no cap number is supplied by this recipe",
        ),
        (
            "reserve_whole_route_output_upper",
            "BROKER_PARENT",
            "reserve a verified branch-aware output upper over the exact eight-role presence matrix before the first native launch",
        ),
        (
            "admit_read_stage_mount_catalogues",
            "BROKER_PARENT",
            "admit complete named read, sandbox-ingress and distinct-payload visibility catalogues before their first side effect",
        ),
        (
            "stage_and_open_payloads",
            "BROKER_PARENT",
            "perform only admitted COPY/BIND ingress and open each distinct mounted-payload interval before child visibility",
        ),
        (
            "launch_worker_then_business",
            "BROKER_PARENT",
            "reserve immediately before each native launch and prove exactly one positive pidfd edge for WORKER followed by BUSINESS; no helper launch is allowed",
        ),
        (
            "execute_h1_business_adapter",
            "WORKER_AND_BUSINESS",
            "execute the future canonical H1 fallback adapter rather than the current root-cap business payload",
        ),
        (
            "seal_pre_reap_business_result",
            "BUSINESS",
            "commit the immutable BUSINESS_RESULT role before child reap without using the pre-reap operational wrapper as that role",
        ),
        (
            "authenticate_protocol_and_reap",
            "BROKER_PARENT",
            "authenticate the complete five-frame protocol, close peer write halves and directly pidfd-reap both children",
        ),
        (
            "render_and_commit_post_reap_roles",
            "BROKER_PARENT",
            "render the seven remaining registered roles, solve/read back the fixed point, and commit no ninth durable wrapper",
        ),
        (
            "observe_peak_and_close_visibility",
            "BROKER_PARENT",
            "after trusted reaps read the retained hierarchy memory.peak OFD, then close mounted visibility intervals and settle all shared receipts",
        ),
        (
            "materialize_and_close",
            "BROKER_PARENT",
            "materialize the future 202-record chain, verify terminal classification, prove no outstanding reservation/mount/binding, then close the route window",
        ),
    )
    return tuple(
        PostDecisionStepV1(index, key, owner, obligation)
        for index, (key, owner, obligation) in enumerate(rows, start=1)
    )


def _predecision_prerequisites() -> tuple[str, ...]:
    return (
        "PRODUCTION_NO_GROUND_CURRENT_IDENTITY_VERIFIER",
        "H1_ROLE_MANIFEST_PROFILE",
        "H1_RUNTIME_PROFILE",
        "H1_BUSINESS_ADAPTER_SOURCE_IDENTITY",
        "BROKER_PARENT_CONTINUOUS_MEMORY_SCOPE_AUTHORITY",
        "OFFICIAL_MEMORY_FORMULA_AUTHORITY",
        "OUTER_BROKER_WORKER_BUSINESS_CAP_OPERAND_AUTHORITIES",
        "BRANCH_COMPLETE_OUTPUT_PRESENCE_MATRIX_AND_UPPER",
        "HASH_INTEGRITY_PROTOCOL_ADMISSION_CATALOGUES",
        "READ_STAGE_MOUNT_CATALOGUES",
        "POSITIVE_TWO_ROLE_NO_HELPER_LAUNCH_CARDINALITY",
        "FORMAL_V7_DIRECT_FALLBACK_UPPER",
        "FORMAL_V7_FALLBACK_ROUTE_DECISION",
    )


def _memory_scopes() -> tuple[MemoryScopeRequirementV1, ...]:
    return (
        MemoryScopeRequirementV1(
            "OUTER",
            ("BROKER_PARENT", "WORKER_PROCESS", "BUSINESS_PROCESS"),
            "OUTER_CGROUP_CAP_BYTES",
            (
                "PREEXECUTION_MEMORY_MAX_READBACK",
                "CONTINUOUS_ROUTE_MEMBERSHIP_PROOF",
                "RETAINED_OUTER_MEMORY_PEAK_OFD",
                "POST_REAP_EMPTY_HIERARCHY_PROOF",
            ),
        ),
        MemoryScopeRequirementV1(
            "BROKER_PARENT",
            ("BROKER_PARENT",),
            "BROKER_PARENT_CGROUP_CAP_BYTES",
            (
                "CONTINUOUS_BROKER_CAP_READBACK",
                "BROKER_ROUTE_WINDOW_MEMBERSHIP_PROOF",
                "BROKER_PEAK_SOURCE_OR_OUTER_INCLUSION_PROOF",
            ),
        ),
        MemoryScopeRequirementV1(
            "WORKER",
            ("WORKER_PROCESS",),
            "ROLE_CGROUP_CAP_BYTES",
            (
                "ROLE_MEMORY_MAX_READBACK",
                "ROLE_MEMBERSHIP_PROOF",
            ),
        ),
        MemoryScopeRequirementV1(
            "BUSINESS",
            ("BUSINESS_PROCESS",),
            "ROLE_CGROUP_CAP_BYTES",
            (
                "ROLE_MEMORY_MAX_READBACK",
                "ROLE_MEMBERSHIP_PROOF",
            ),
        ),
    )


def _output_roles() -> tuple[OutputRoleRequirementV1, ...]:
    semantics = {
        "BUSINESS_RESULT": (
            "CANONICAL_H1_FALLBACK_RESULT_AND_TRACE",
            "IMMUTABLE_PRE_REAP_ROLE_BYTES",
        ),
        "OPERATIONAL_TRACE": (
            "ORDERED_ACCESS_CAP_LAUNCH_REAP_READ_WRITE_EVENTS",
            "FAILURE_PREFIX_PRESERVED",
        ),
        "TERMINAL_ARTIFACT": (
            "EXACT_FQ9_CLASS_AND_CODE",
            "CAP_EXHAUSTION_NEVER_INFEASIBILITY",
        ),
        "COUNTER_RECORD_SET": (
            "EXACT_202_V6_COUNTER_RECORDS",
            "NATIVE_ZERO_AND_FAILURE_PREFIX_PRESERVED",
        ),
        "WORK_VECTOR": ("EXACT_COUNTER_RECORD_PROJECTION",),
        "COMPARISON_VECTOR": ("EXACT_SHARED_AXIS_PROJECTION",),
        "ACTUAL_PROJECTION_PROOF": (
            "WORK_VECTOR_AND_COMPARISON_VECTOR_ID_EQUALITY",
            "SELECTED_UPPER_COMPLIANCE_REPLAY",
        ),
        "OUTPUT_MANIFEST": (
            "FIRST_SEVEN_ROLE_HASHES_AND_EXTENTS",
            "EMBED_CANDIDATE_TOTAL_NOT_OWN_HASH",
            "NO_SELF_HASH_OR_NINTH_DURABLE_WRAPPER",
        ),
    }
    result = []
    for role in output_fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES:
        result.append(
            OutputRoleRequirementV1(
                role,
                "BUSINESS" if role == "BUSINESS_RESULT" else "BROKER_PARENT",
                "PRE_REAP_IMMUTABLE"
                if role == "BUSINESS_RESULT"
                else "POST_REAP_FINALIZATION",
                semantics[role],
            )
        )
    return tuple(result)


def _failure_branches() -> tuple[FailureBranchRequirementV1, ...]:
    rows = (
        (
            "EXACT_INFEASIBLE_SUCCESS",
            "INFEASIBILITY_CERTIFICATE",
            "FULL_GROUND_EXACT_INFEASIBLE",
            BusinessResultPresenceV1.REQUIRED,
            "ALL_EIGHT_AFTER_SUCCESSFUL_FINALIZATION",
        ),
        (
            "FALLBACK_CAP_EXHAUSTED",
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "FALLBACK_CAP_EXHAUSTED",
            BusinessResultPresenceV1.REQUIRED,
            "ALL_EIGHT_AFTER_SUCCESSFUL_FINALIZATION",
        ),
        (
            "PROTOCOL_OR_ACCOUNTING_FAILURE",
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "PROTOCOL_FAILURE",
            BusinessResultPresenceV1.PHASE_SPLIT_REQUIRED,
            "BRANCH_PRESENCE_MATRIX_REQUIRED",
        ),
        (
            "INTEGRITY_FAILURE",
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "INTEGRITY_FAILURE",
            BusinessResultPresenceV1.PHASE_SPLIT_REQUIRED,
            "BRANCH_PRESENCE_MATRIX_REQUIRED",
        ),
        (
            "AMBIGUOUS_NATIVE_LAUNCH",
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "PROTOCOL_FAILURE",
            BusinessResultPresenceV1.TYPED_ABSENT_REQUIRED,
            "BROKER_SUBSET_WITH_TYPED_BUSINESS_ABSENCE_IF_FINALIZATION_SUCCEEDS",
        ),
        (
            "OUTPUT_FINALIZATION_FAILURE",
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "PROTOCOL_FAILURE",
            BusinessResultPresenceV1.PHASE_SPLIT_REQUIRED,
            "PRESERVE_COMMITTED_SUBSET_AND_TYPED_UNCOMMITTED_ABSENCE_OFFICIAL_INVALID",
        ),
        (
            "H1_BUSINESS_ADAPTER_FAILURE",
            "ATTEMPT_CLOSURE_NONCERTIFICATE",
            "PROTOCOL_FAILURE",
            BusinessResultPresenceV1.PHASE_SPLIT_REQUIRED,
            "BRANCH_PRESENCE_MATRIX_REQUIRED",
        ),
    )
    preserve = (
        "ALL_ACTUAL_WORK_BEFORE_FAILURE",
        "ALL_ACTUAL_IO_BEFORE_FAILURE",
        "NATIVE_LAUNCH_AND_EXIT_FACTS",
        "NO_INFEASIBILITY_FROM_CAP_OR_PROTOCOL_FAILURE",
    )
    return tuple(
        FailureBranchRequirementV1(
            key, terminal_class, code, presence, presence_rule, preserve
        )
        for key, terminal_class, code, presence, presence_rule in rows
    )


@dataclass(frozen=True, slots=True)
class H1DirectFallbackTwoRoleRecipeProfileV1:
    _issuer: InitVar[object]
    _payload_bytes: bytes = field(init=False, repr=False)
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("H1 two-role recipe profile is issuer-owned")
        payload = self._build_payload()
        object.__setattr__(self, "_payload_bytes", canonical_json_bytes(payload))
        object.__setattr__(self, "_profile_id", content_id(PROFILE_DOMAIN, payload))

    def _build_payload(self) -> dict[str, Any]:
        source = source_v1.freeze_direct_fallback_shared_source_manifest_v1()
        return {
            "schema": "acfqp.construction_k7_h1_direct_fallback_two_role_recipe_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_manifest_id": source.manifest_id,
            "source_manifest_sha256": hashlib.sha256(source.canonical_bytes).hexdigest(),
            "reference_existing_root_cap_role_manifest_profile_id": role_manifest_v2.official_v075_k7_production_role_manifest_profile_v2().profile_id,
            "reference_existing_root_cap_runtime_profile_id": runtime_v2.official_v075_k7_production_broker_runtime_profile_v2().profile_id,
            "required_h1_role_manifest_profile_id": None,
            "required_h1_runtime_profile_id": None,
            "root_cap_profiles_are_h1_profiles": False,
            "required_production_roles": ["WORKER", "BUSINESS"],
            "required_role_order": ["WORKER", "BUSINESS"],
            "production_manifest_instance_id": None,
            "production_runtime_envelope_id": None,
            "instance_binding_status": BindingStatusV1.EXACT_PROFILE_BOUND_INSTANCE_REQUIRED.value,
            "current_root_cap_manifest_or_runtime_instance_accepted": False,
            "h1_business_adapter_present": False,
            "production_current_identity_verifier_present": False,
            "preselection_kernel_step_allowed": False,
            "preselection_fallback_solver_allowed": False,
            "post_decision_steps": [row.to_document() for row in _post_decision_steps()],
            "required_predecision_prerequisites": list(_predecision_prerequisites()),
            "predecision_prerequisites_satisfied": False,
            "postdecision_scope_or_formula_resolution_allowed": False,
            "post_decision_steps_are_success_or_postbusiness_order": True,
            "failure_transition_rule": "on any failure stop ordinary sequence, preserve the exact prefix, and enter the branch-presence-matrix renderer",
            "official_memory_formula": None,
            "safe_memory_formula_candidates": [
                "OUTER_CGROUP_CAP_BYTES if OUTER continuously contains BROKER_PARENT+WORKER_PROCESS+BUSINESS_PROCESS",
                "min(OUTER_CGROUP_CAP_BYTES,BROKER_PARENT_CGROUP_CAP_BYTES+WORKER_ROLE_CGROUP_CAP_BYTES+BUSINESS_ROLE_CGROUP_CAP_BYTES)",
            ],
            "source_manifest_two_child_role_formula_is_complete_route_formula": False,
            "memory_scope_status": MemoryScopeStatusV1.UNRESOLVED.value,
            "memory_scope_requirements": [row.to_document() for row in _memory_scopes()],
            "broker_parent_child_only_peak_is_complete_route_peak": False,
            "broker_parent_allowed_outside_continuous_route_scope": False,
            "broker_parent_resolution_requirement": "continuous-cap-and-peak-coverage-from-first-post-decision-operation-through-output-finalization; revise hierarchy or formula before execution",
            "numeric_memory_operand_authority_ids": None,
            "numeric_memory_upper": None,
            "output_roles": [row.to_document() for row in _output_roles()],
            "durable_output_role_registry_count": len(output_fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES),
            "ninth_durable_output_wrapper_allowed": False,
            "output_manifest_self_hash_allowed": False,
            "successful_finalization_requires_all_eight_roles": True,
            "postbusiness_finalization_failure_guarantees_all_eight_roles": False,
            "failed_finalization_preserves_committed_role_subset": True,
            "failed_finalization_requires_typed_uncommitted_role_absence": True,
            "failed_finalization_official_run_valid": False,
            "broker_output_recovery_renderer_present": False,
            "broker_fabricated_business_result_allowed": False,
            "early_failure_typed_business_result_absence_allowed": True,
            "early_failure_broker_owned_role_subset": list(
                output_fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES[1:]
            ),
            "early_failure_output_manifest_requires_typed_business_result_absence": True,
            "branch_presence_matrix_authority_id": None,
            "output_fixed_point_result_id": None,
            "output_failure_branch_catalogue_id": None,
            "required_failure_branches": [row.to_document() for row in _failure_branches()],
            "minimum_failure_branch_set_claimed_complete": False,
            "branch_complete_renderer_and_reachability_proof_required": True,
            "unregistered_reachable_failure_branch_allowed": False,
            "read_family_catalogue_id": None,
            "staging_family_catalogue_id": None,
            "mount_interval_catalogue_id": None,
            "hash_purpose_catalogue_id": None,
            "integrity_obligation_catalogue_id": None,
            "protocol_obligation_catalogue_id": None,
            "path_specific_shared_admission_catalogue_id": None,
            "control_cap_check_formula_authority_id": None,
            "process_launch_aggregate_candidate": None,
            "numeric_aggregate_candidate_issued": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
            "construction_only": True,
            "blockers": list(BLOCKERS),
        }

    def _payload(self) -> dict[str, Any]:
        document = loads_canonical_json(self._payload_bytes)
        if type(document) is not dict:
            _fail("H1 two-role recipe profile snapshot is malformed")
        return document

    @property
    def profile_id(self) -> str:
        if content_id(PROFILE_DOMAIN, self._payload()) != self._profile_id:
            _fail("H1 two-role recipe profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_two_role_recipe_profile_id": self.profile_id}


_OFFICIAL_PROFILE = H1DirectFallbackTwoRoleRecipeProfileV1(_PROFILE_ISSUER)


def official_h1_direct_fallback_two_role_recipe_profile_v1(
) -> H1DirectFallbackTwoRoleRecipeProfileV1:
    return _OFFICIAL_PROFILE


@dataclass(frozen=True, slots=True)
class LegacyH1PreexecutionProjectionV1:
    preexecution_sha256: str
    current_identity_attestation_id: str
    exact_infeasibility_identity_id: str
    durable_proof_id: str
    preexecution_candidate_id: str
    route_decision_context_id: str
    decision_point_id: str
    legacy_selected_upper_id: str
    legacy_route_decision_id: str
    structural_id: str
    query_id: str
    selected_plan_id: str
    threshold_profile_id: str
    build_epoch_id: str
    kernel_id: str
    logical_occurrence_id: str
    route_attempt_id: str

    def __post_init__(self) -> None:
        for field_name in (
            "current_identity_attestation_id",
            "exact_infeasibility_identity_id",
            "durable_proof_id",
            "preexecution_candidate_id",
            "route_decision_context_id",
            "decision_point_id",
            "legacy_selected_upper_id",
            "legacy_route_decision_id",
            "structural_id",
            "query_id",
            "selected_plan_id",
            "threshold_profile_id",
            "build_epoch_id",
            "kernel_id",
            "logical_occurrence_id",
            "route_attempt_id",
        ):
            _cid(getattr(self, field_name), field_name)
        if (
            type(self.preexecution_sha256) is not str
            or len(self.preexecution_sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.preexecution_sha256)
        ):
            _fail("preexecution SHA-256 is invalid")

    def to_document(self) -> dict[str, Any]:
        return {
            "preexecution_candidate_sha256": self.preexecution_sha256,
            "current_identity_attestation_id": self.current_identity_attestation_id,
            "exact_infeasibility_identity_id": self.exact_infeasibility_identity_id,
            "durable_proof_id": self.durable_proof_id,
            "preexecution_candidate_id": self.preexecution_candidate_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "decision_point_id": self.decision_point_id,
            "legacy_selected_upper_id": self.legacy_selected_upper_id,
            "legacy_route_decision_id": self.legacy_route_decision_id,
            "structural_id": self.structural_id,
            "query_id": self.query_id,
            "selected_plan_id": self.selected_plan_id,
            "threshold_profile_id": self.threshold_profile_id,
            "BuildEpoch_id": self.build_epoch_id,
            "kernel_id": self.kernel_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "projection_status": BindingStatusV1.STRUCTURAL_BYTES_ONLY_NOT_SEMANTIC_AUTHORITY.value,
            "source_bytes_semantically_verified": False,
            "content_addressing_authenticates_current_identity": False,
            "claimed_h1_semantics_authenticated": False,
            "durable_proof_bytes_bound": False,
            "current_kernel_law_authenticated": False,
            "production_current_identity_verifier_required": True,
            "claimed_horizon": 1,
            "postrun_acquisition_required": False,
            "legacy_current_identity_builder_used_ground_replay": True,
            "legacy_current_identity_allowed_as_production_preselection_verifier": False,
            "legacy_upper_used_as_formal_v7_upper": False,
            "legacy_route_decision_used_as_formal_v7_decision": False,
        }


def _source_projection(preexecution_candidate_bytes: bytes) -> LegacyH1PreexecutionProjectionV1:
    pre = _canonical_object(
        preexecution_candidate_bytes, "legacy H1 preexecution candidate"
    )
    if (
        frozenset(pre) != _PREEXECUTION_FIELDS
        or pre.get("schema")
        != "acfqp.construction_k7_canonical_infeasible_fallback_preexecution.v1"
        or pre.get("profile_key")
        != "construction_k7_canonical_infeasible_fallback_acquisition_v1"
        or pre.get("scope") != "RAW_IN_PROCESS_MARGINAL_SEGMENT"
        or pre.get("production_authorized") is not False
        or pre.get("official_execution_allowed") is not False
    ):
        _fail("source bytes are not the legacy canonical H1 preexecution family")
    pre_id = _verify_embedded_id(
        pre,
        id_field="direct_fallback_preexecution_candidate_id",
        domain=CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_PREEXECUTION_V1_DOMAIN,
        label="H1 preexecution candidate",
    )
    current = pre.get("current_identity_attestation") if type(pre) is dict else None
    if type(current) is not dict or frozenset(current) != _CURRENT_IDENTITY_FIELDS:
        _fail("H1 current-identity attestation fields are not exact")
    current_id = _verify_embedded_id(
        current,
        id_field="current_identity_attestation_id",
        domain=CONSTRUCTION_K7_CANONICAL_INFEASIBLE_FALLBACK_CURRENT_IDENTITY_V1_DOMAIN,
        label="H1 current-identity attestation",
    )
    try:
        durable_identity = DurableExactInfeasibilityIdentityV1.from_dict(
            current["identity"]
        )
        context = RouteDecisionContextV1.from_dict(pre["route_context"])
        point = DecisionPointV1.from_dict(pre["decision_point"])
        upper = RouteUpperBoundEnvelopeV1.from_dict(pre["route_upper"])
        decision = MarginalRouteDecisionV1.from_dict(pre["route_decision"])
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error(
            "embedded H1 typed route chain failed bytes-only replay"
        ) from error
    if (
        pre.get("current_identity_attestation_id") != current_id
        or pre.get("route_decision_frozen_before_kernel_access") is not True
        or pre.get("selected_route") != RouteSelection.FALLBACK.value
        or pre.get("production_route_authority") is not False
        or current.get("build_lane") != "EVALUATION"
        or current.get("charged_as_operational_route_work") is not False
        or current.get("live_kernel_and_query_replayed") is not True
        or current.get("production_authority") is not False
        or context.route_decision_context_id != point.route_decision_context_id
        or upper.decision_point_id != point.decision_point_id
        or any(
            getattr(upper, field_name) != getattr(context, field_name)
            for field_name in (
                "preregistration_id",
                "protocol_id",
                "comparison_profile_id",
                "counter_registry_id",
                "structural_id",
                "query_id",
                "selected_plan_id",
                "threshold_profile_id",
                "build_epoch_id",
                "logical_occurrence_id",
                "route_attempt_id",
            )
        )
        or decision.decision_point_id != point.decision_point_id
        or decision.selected_route is not RouteSelection.FALLBACK
        or upper.route_kind is not RouteKind.DIRECT_FALLBACK
        or decision.selected_upper_id != upper.route_upper_bound_envelope_id
        or context.structural_id != durable_identity.structural_id
        or context.query_id != durable_identity.query_id
        or context.threshold_profile_id != durable_identity.threshold_profile_id
        or context.build_epoch_id != durable_identity.build_epoch_id
    ):
        _fail("embedded H1 identities or frozen FALLBACK chain crossed")
    return LegacyH1PreexecutionProjectionV1(
        hashlib.sha256(preexecution_candidate_bytes).hexdigest(),
        current_id,
        durable_identity.exact_infeasibility_identity_id,
        _cid(pre.get("durable_proof_id"), "durable proof"),
        pre_id,
        context.route_decision_context_id,
        point.decision_point_id,
        upper.route_upper_bound_envelope_id,
        decision.route_decision_id,
        context.structural_id,
        context.query_id,
        context.selected_plan_id,
        context.threshold_profile_id,
        context.build_epoch_id,
        durable_identity.kernel_id,
        context.logical_occurrence_id,
        context.route_attempt_id,
    )


@dataclass(frozen=True, slots=True)
class H1DirectFallbackTwoRoleRecipeV1:
    _issuer: InitVar[object]
    source: LegacyH1PreexecutionProjectionV1
    _recipe_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RECIPE_ISSUER or type(self.source) is not LegacyH1PreexecutionProjectionV1:
            _fail("H1 two-role recipe is caller-minted")
        object.__setattr__(self, "_recipe_id", content_id(RECIPE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        profile = official_h1_direct_fallback_two_role_recipe_profile_v1()
        return {
            "schema": "acfqp.construction_k7_h1_direct_fallback_two_role_recipe.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_two_role_recipe_profile_id": profile.profile_id,
            "legacy_h1_preexecution_projection": self.source.to_document(),
            "reference_existing_root_cap_role_manifest_profile_id": profile.to_document()["reference_existing_root_cap_role_manifest_profile_id"],
            "reference_existing_root_cap_runtime_profile_id": profile.to_document()["reference_existing_root_cap_runtime_profile_id"],
            "required_h1_role_manifest_profile_id": None,
            "required_h1_runtime_profile_id": None,
            "production_role_manifest_id": None,
            "production_runtime_envelope_id": None,
            "h1_business_adapter_id": None,
            "production_current_identity_verifier_id": None,
            "aggregate_operand_catalogue_id": None,
            "numeric_shared_cap_values": None,
            "numeric_aggregate_cap_candidate": None,
            "formal_v7_route_upper_id": None,
            "formal_v7_route_decision_id": None,
            "postrun_acquisition_required": False,
            "bytes_only_projection_calls_kernel_step": False,
            "bytes_only_projection_calls_fallback_solver": False,
            "bytes_only_projection_is_semantic_current_identity_authority": False,
            "caller_rehashable_projection_used_as_production_authority": False,
            "current_root_cap_instance_accepted": False,
            "production_execution_started": False,
            "counter_records_issued": 0,
            "work_vectors_issued": 0,
            "comparison_vectors_issued": 0,
            "terminal_artifacts_issued": 0,
            "numeric_aggregate_candidate_issued": False,
            "formal_v7_route_authority_present": False,
            "official_execution_allowed": False,
            "construction_only": True,
            "blockers": list(BLOCKERS),
        }

    @property
    def recipe_id(self) -> str:
        retained = _LIVE_RECIPES.get(id(self))
        current = canonical_json_bytes(self._unchecked_document())
        if (
            content_id(RECIPE_DOMAIN, self._payload()) != self._recipe_id
            or retained is None
            or retained[0] is not self
            or not hmac.compare_digest(retained[1], current)
        ):
            _fail("H1 two-role recipe changed or lost issuer retention")
        return self._recipe_id

    def _unchecked_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_direct_fallback_two_role_recipe_id": self._recipe_id}

    @property
    def canonical_bytes(self) -> bytes:
        _ = self.recipe_id
        return canonical_json_bytes(self._unchecked_document())

    def to_document(self) -> dict[str, Any]:
        _ = self.recipe_id
        return self._unchecked_document()


def freeze_h1_direct_fallback_two_role_recipe_v1(
    *, preexecution_candidate_bytes: bytes
) -> H1DirectFallbackTwoRoleRecipeV1:
    source = _source_projection(preexecution_candidate_bytes)
    recipe = H1DirectFallbackTwoRoleRecipeV1(_RECIPE_ISSUER, source)
    raw = canonical_json_bytes(recipe._unchecked_document())
    _LIVE_RECIPES[id(recipe)] = (recipe, raw)
    return recipe


def verify_h1_direct_fallback_two_role_recipe_bytes_v1(
    *, raw: bytes, preexecution_candidate_bytes: bytes
) -> H1DirectFallbackTwoRoleRecipeV1:
    document = _canonical_object(raw, "H1 two-role recipe")
    replay = freeze_h1_direct_fallback_two_role_recipe_v1(
        preexecution_candidate_bytes=preexecution_candidate_bytes
    )
    if document != replay.to_document():
        _fail("H1 two-role recipe differs from exact construction replay")
    return replay


__all__ = (
    "BLOCKERS",
    "BindingStatusV1",
    "CONSTRUCTION_ONLY",
    "ConstructionK7H1DirectFallbackTwoRoleRecipeV1Error",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "H1DirectFallbackTwoRoleRecipeProfileV1",
    "H1DirectFallbackTwoRoleRecipeV1",
    "FailureBranchRequirementV1",
    "LegacyH1PreexecutionProjectionV1",
    "MemoryScopeRequirementV1",
    "MemoryScopeStatusV1",
    "NUMERIC_AGGREGATE_CANDIDATE_ISSUED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OutputRoleRequirementV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "PostDecisionStepV1",
    "RecipeBlockerV1",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "freeze_h1_direct_fallback_two_role_recipe_v1",
    "official_h1_direct_fallback_two_role_recipe_profile_v1",
    "verify_h1_direct_fallback_two_role_recipe_bytes_v1",
)
