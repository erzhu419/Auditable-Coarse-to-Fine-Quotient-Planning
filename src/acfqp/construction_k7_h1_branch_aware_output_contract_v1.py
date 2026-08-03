"""Construction-only H1 branch-aware eight-role output contract.

This module replaces the opaque-renderer and vague ``PHASE_SPLIT`` gaps left by
the Contract 2.0.50 recipe.  It freezes the exact eight-role universe, a
branch-complete presence matrix, owner-separated typed fixture inputs, canonical
module-owned serializers, and a deterministic subset-aware output-byte fixed
point.  It does not provide production business semantics, numeric aggregate
authorities, a V7 route authority, or permission to execute an official run.

The objects here are in-memory construction records.  They are not a ninth
operational output and may not be serialized beside the eight registered roles
as an unregistered wrapper.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from enum import Enum
import hashlib
import hmac
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_ARTIFACT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_BROKER_FIXTURE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_BUSINESS_FIXTURE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_FIXED_POINT_ITERATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_FIXED_POINT_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_INPUT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_ROLE_ARTIFACT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.51"
PROFILE_KEY = "construction_k7_h1_branch_aware_output_contract_v1"

CONSTRUCTION_ONLY = True
OFFICIAL_EXECUTION_ALLOWED = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
NUMERIC_AGGREGATE_CANDIDATE_ISSUED = False
PRODUCTION_H1_BUSINESS_ADAPTER_PRESENT = False
PRODUCTION_OUTPUT_SEMANTIC_INPUTS_PRESENT = False
COUNTER_COMPLETENESS_GATE_RUN = False
WORKLOAD_ECONOMICS_GATE_RUN = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None

PROFILE_DOMAIN = CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_PROFILE_V1_DOMAIN
BUSINESS_FIXTURE_DOMAIN = (
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_BUSINESS_FIXTURE_V1_DOMAIN
)
BROKER_FIXTURE_DOMAIN = (
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_BROKER_FIXTURE_V1_DOMAIN
)
STRUCTURAL_INPUT_DOMAIN = CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_INPUT_V1_DOMAIN
ROLE_ARTIFACT_DOMAIN = (
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_ROLE_ARTIFACT_V1_DOMAIN
)
ARTIFACT_SET_DOMAIN = (
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_ARTIFACT_SET_V1_DOMAIN
)
ITERATION_DOMAIN = (
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_FIXED_POINT_ITERATION_V1_DOMAIN
)
RESULT_DOMAIN = (
    CONSTRUCTION_K7_H1_BRANCH_AWARE_OUTPUT_FIXED_POINT_RESULT_V1_DOMAIN
)

REQUESTED_PHASE3E_DOMAIN_TAGS = (
    PROFILE_DOMAIN,
    BUSINESS_FIXTURE_DOMAIN,
    BROKER_FIXTURE_DOMAIN,
    STRUCTURAL_INPUT_DOMAIN,
    ROLE_ARTIFACT_DOMAIN,
    ARTIFACT_SET_DOMAIN,
    ITERATION_DOMAIN,
    RESULT_DOMAIN,
)
if len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS):
    raise RuntimeError("H1 branch-aware output domains are not role-separated")
if not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS:
    raise RuntimeError("H1 branch-aware output domains are not centrally registered")

MAX_ROLE_BYTES = 256 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_FIXED_POINT_ITERATIONS = 32
TERMINAL_REPLAY_COUNT = 2

MISSING_PRODUCTION_SEMANTIC_INPUTS = (
    "production_h1_business_result_adapter",
    "production_operational_trace_semantics",
    "production_terminal_classification_semantics",
    "production_counter_record_set",
    "production_work_vector",
    "production_comparison_vector",
    "production_actual_projection_proof",
    "production_output_manifest_commit_authority",
)


class ConstructionK7H1BranchAwareOutputContractV1Error(ValueError):
    """A branch, owner boundary, rendering, or fixed point failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1BranchAwareOutputContractV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BranchAwareOutputContractV1Error(
            f"{label} must be one exact lowercase content ID"
        ) from error


def _canonical_object(raw: Any, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty exact bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BranchAwareOutputContractV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _exact_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        _fail(f"{label} must be an exact integer >= {minimum}")
    return value


def _domain_content_id(domain: str, payload: Mapping[str, Any]) -> str:
    if domain not in REQUESTED_PHASE3E_DOMAIN_TAGS:
        _fail("undeclared H1 branch-aware output content domain")
    return content_id(domain, dict(payload))


_RECIPE_CONTEXT_CACHE: dict[int, tuple[Any, dict[str, Any]]] = {}
_RECIPE_CONTEXT_FIELDS = frozenset(
    {
        "upstream_h1_recipe_id",
        "upstream_h1_recipe_profile_id",
        "preexecution_candidate_id",
        "RouteDecisionContext_id",
        "decision_point_id",
        "structural_id",
        "query_id",
        "selected_plan_id",
        "threshold_profile_id",
        "BuildEpoch_id",
        "kernel_id",
        "logical_occurrence_id",
        "route_attempt_id",
    }
)


def _verify_recipe(
    value: Any,
) -> recipe_v1.H1DirectFallbackTwoRoleRecipeV1:
    if type(value) is not recipe_v1.H1DirectFallbackTwoRoleRecipeV1:
        _fail("output context requires one issuer-owned Contract 2.0.50 recipe")
    try:
        recipe_id = value.recipe_id
        source = value.source.to_document()
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BranchAwareOutputContractV1Error(
            "upstream H1 recipe failed exact live verification"
        ) from error
    required = _RECIPE_CONTEXT_FIELDS - {
        "upstream_h1_recipe_id",
        "upstream_h1_recipe_profile_id",
    }
    if not required <= set(source):
        _fail("upstream H1 recipe source projection is incomplete")
    context = {
        "upstream_h1_recipe_id": recipe_id,
        "upstream_h1_recipe_profile_id": (
            recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1().profile_id
        ),
        "preexecution_candidate_id": source["preexecution_candidate_id"],
        "RouteDecisionContext_id": source["RouteDecisionContext_id"],
        "decision_point_id": source["decision_point_id"],
        "structural_id": source["structural_id"],
        "query_id": source["query_id"],
        "selected_plan_id": source["selected_plan_id"],
        "threshold_profile_id": source["threshold_profile_id"],
        "BuildEpoch_id": source["BuildEpoch_id"],
        "kernel_id": source["kernel_id"],
        "logical_occurrence_id": source["logical_occurrence_id"],
        "route_attempt_id": source["route_attempt_id"],
    }
    _RECIPE_CONTEXT_CACHE[id(value)] = (value, context)
    return value


def _recipe_context(
    value: recipe_v1.H1DirectFallbackTwoRoleRecipeV1,
) -> dict[str, Any]:
    retained = _RECIPE_CONTEXT_CACHE.get(id(value))
    if retained is None or retained[0] is not value:
        _verify_recipe(value)
        retained = _RECIPE_CONTEXT_CACHE.get(id(value))
    if retained is None or retained[0] is not value:  # pragma: no cover
        _fail("upstream H1 recipe context is not issuer retained")
    return dict(retained[1])


class H1OperationalOutputRoleV1(str, Enum):
    BUSINESS_RESULT = "BUSINESS_RESULT"
    OPERATIONAL_TRACE = "OPERATIONAL_TRACE"
    TERMINAL_ARTIFACT = "TERMINAL_ARTIFACT"
    COUNTER_RECORD_SET = "COUNTER_RECORD_SET"
    WORK_VECTOR = "WORK_VECTOR"
    COMPARISON_VECTOR = "COMPARISON_VECTOR"
    ACTUAL_PROJECTION_PROOF = "ACTUAL_PROJECTION_PROOF"
    OUTPUT_MANIFEST = "OUTPUT_MANIFEST"


REGISTERED_OPERATIONAL_OUTPUT_ROLES = tuple(
    role.value for role in H1OperationalOutputRoleV1
)
BUSINESS_RESULT_ROLE = H1OperationalOutputRoleV1.BUSINESS_RESULT.value
OUTPUT_MANIFEST_ROLE = H1OperationalOutputRoleV1.OUTPUT_MANIFEST.value
BROKER_OUTPUT_ROLE_ORDER = REGISTERED_OPERATIONAL_OUTPUT_ROLES[1:]


class H1OutputOwnerV1(str, Enum):
    BUSINESS = "H1_BUSINESS_ADAPTER"
    BROKER = "H1_TRUSTED_BROKER"


class H1BusinessOutcomeV1(str, Enum):
    EXACT_INFEASIBILITY_RESULT = "EXACT_INFEASIBILITY_RESULT"
    FALLBACK_CAP_EXHAUSTED_RESULT = "FALLBACK_CAP_EXHAUSTED_RESULT"
    COMMITTED_BEFORE_LATER_FAILURE = "COMMITTED_BEFORE_LATER_FAILURE"


class H1OutputBranchV1(str, Enum):
    EXACT_INFEASIBLE_SUCCESS = "EXACT_INFEASIBLE_SUCCESS"
    FALLBACK_CAP_EXHAUSTED = "FALLBACK_CAP_EXHAUSTED"
    PROTOCOL_FAILURE = "PROTOCOL_FAILURE"
    INTEGRITY_FAILURE = "INTEGRITY_FAILURE"
    AMBIGUOUS_NATIVE_LAUNCH = "AMBIGUOUS_NATIVE_LAUNCH"
    H1_BUSINESS_ADAPTER_FAILURE = "H1_BUSINESS_ADAPTER_FAILURE"


class H1OutputCommitPhaseV1(str, Enum):
    BUSINESS_AND_BROKER_FINALIZED = "BUSINESS_AND_BROKER_FINALIZED"
    PRE_BUSINESS_FAILURE_BROKER_FINALIZED = (
        "PRE_BUSINESS_FAILURE_BROKER_FINALIZED"
    )
    BUSINESS_COMMITTED_FAILURE_BROKER_FINALIZED = (
        "BUSINESS_COMMITTED_FAILURE_BROKER_FINALIZED"
    )
    BUSINESS_COMMITTED_OUTPUT_FINALIZATION_CLOSURE_FAILURE = (
        "BUSINESS_COMMITTED_OUTPUT_FINALIZATION_CLOSURE_FAILURE"
    )
    PRE_BUSINESS_OUTPUT_FINALIZATION_CLOSURE_FAILURE = (
        "PRE_BUSINESS_OUTPUT_FINALIZATION_CLOSURE_FAILURE"
    )
    PRE_BUSINESS_OUTPUT_FINALIZATION_IN_PROGRESS_FAILURE = (
        "PRE_BUSINESS_OUTPUT_FINALIZATION_IN_PROGRESS_FAILURE"
    )
    POST_BUSINESS_OUTPUT_FINALIZATION_IN_PROGRESS_FAILURE = (
        "POST_BUSINESS_OUTPUT_FINALIZATION_IN_PROGRESS_FAILURE"
    )


_FAILURE_REACHABILITY = (
    (H1OutputBranchV1.PROTOCOL_FAILURE, ("PRE_BUSINESS", "POST_BUSINESS")),
    (H1OutputBranchV1.INTEGRITY_FAILURE, ("PRE_BUSINESS", "POST_BUSINESS")),
    (H1OutputBranchV1.AMBIGUOUS_NATIVE_LAUNCH, ("PRE_BUSINESS",)),
    (H1OutputBranchV1.H1_BUSINESS_ADAPTER_FAILURE, ("PRE_BUSINESS",)),
)
_CASE_NAMES = ["EXACT_INFEASIBLE_SUCCESS", "FALLBACK_CAP_EXHAUSTED"]
for _business_branch in (
    H1OutputBranchV1.EXACT_INFEASIBLE_SUCCESS,
    H1OutputBranchV1.FALLBACK_CAP_EXHAUSTED,
):
    _CASE_NAMES.extend(
        f"{_business_branch.value}_OUTPUT_FINALIZATION_FAILURE_P{prefix}"
        for prefix in range(len(BROKER_OUTPUT_ROLE_ORDER) + 1)
    )
for _branch, _business_phases in _FAILURE_REACHABILITY:
    for _business_phase in _business_phases:
        _CASE_NAMES.extend(
            f"{_branch.value}_{_business_phase}_P{prefix}"
            for prefix in range(len(BROKER_OUTPUT_ROLE_ORDER) + 1)
        )
        _CASE_NAMES.append(
            f"{_branch.value}_{_business_phase}_P7_CLOSURE_FAILURE"
        )
H1OutputCaseV1 = Enum(
    "H1OutputCaseV1",
    {name: name for name in _CASE_NAMES},
    type=str,
    module=__name__,
)


@dataclass(frozen=True, slots=True)
class H1OutputPresenceRowV1:
    case: H1OutputCaseV1
    branch: H1OutputBranchV1
    commit_phase: H1OutputCommitPhaseV1
    business_result_committed: bool
    broker_prefix_count: int
    present_roles: tuple[str, ...]
    absent_roles: tuple[str, ...]
    output_finalization_failed: bool
    invalidates_official_run: bool

    def __post_init__(self) -> None:
        if type(self.case) is not H1OutputCaseV1:
            _fail("presence row case must be one exact registered case")
        if type(self.branch) is not H1OutputBranchV1:
            _fail("presence row branch must be exact")
        if type(self.commit_phase) is not H1OutputCommitPhaseV1:
            _fail("presence row commit phase must be exact")
        if type(self.business_result_committed) is not bool:
            _fail("business-result committed flag must be exact bool")
        if type(self.output_finalization_failed) is not bool:
            _fail("output-finalization-failed flag must be exact bool")
        if type(self.invalidates_official_run) is not bool:
            _fail("invalidates-official-run flag must be exact bool")
        _exact_int(self.broker_prefix_count, "broker prefix count")
        if self.broker_prefix_count > len(BROKER_OUTPUT_ROLE_ORDER):
            _fail("broker prefix count exceeds the registered broker roles")
        expected_present = (
            ((BUSINESS_RESULT_ROLE,) if self.business_result_committed else ())
            + BROKER_OUTPUT_ROLE_ORDER[: self.broker_prefix_count]
        )
        expected_present = tuple(
            role
            for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES
            if role in expected_present
        )
        expected_absent = tuple(
            role
            for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES
            if role not in expected_present
        )
        if self.present_roles != expected_present or self.absent_roles != expected_absent:
            _fail("presence row is not the exact business-plus-broker-prefix partition")
        if set(self.present_roles) & set(self.absent_roles):
            _fail("presence row overlaps present and absent roles")
        if set(self.present_roles) | set(self.absent_roles) != set(
            REGISTERED_OPERATIONAL_OUTPUT_ROLES
        ):
            _fail("presence row does not cover the exact eight-role universe")

    def to_document(self) -> dict[str, Any]:
        return {
            "case": self.case.value,
            "branch": self.branch.value,
            "commit_phase": self.commit_phase.value,
            "business_result_committed": self.business_result_committed,
            "broker_prefix_count": self.broker_prefix_count,
            "present_roles": list(self.present_roles),
            "absent_roles": list(self.absent_roles),
            "output_finalization_failed": self.output_finalization_failed,
            "invalidates_official_run": self.invalidates_official_run,
        }


def _presence_row(
    case: H1OutputCaseV1,
) -> H1OutputPresenceRowV1:
    if type(case) is not H1OutputCaseV1:
        try:
            case = H1OutputCaseV1(case)
        except (TypeError, ValueError) as error:
            raise ConstructionK7H1BranchAwareOutputContractV1Error(
                f"unknown output case {case!r}"
            ) from error

    fixed: dict[H1OutputCaseV1, tuple[H1OutputBranchV1, H1OutputCommitPhaseV1, bool]] = {
        H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS: (
            H1OutputBranchV1.EXACT_INFEASIBLE_SUCCESS,
            H1OutputCommitPhaseV1.BUSINESS_AND_BROKER_FINALIZED,
            True,
        ),
        H1OutputCaseV1.FALLBACK_CAP_EXHAUSTED: (
            H1OutputBranchV1.FALLBACK_CAP_EXHAUSTED,
            H1OutputCommitPhaseV1.BUSINESS_AND_BROKER_FINALIZED,
            True,
        ),
    }
    if case in fixed:
        branch, phase, business = fixed[case]
        prefix = len(BROKER_OUTPUT_ROLE_ORDER)
        finalization_failed = False
    else:
        name = case.value
        closure_failed = name.endswith("_P7_CLOSURE_FAILURE")
        prefix = (
            len(BROKER_OUTPUT_ROLE_ORDER)
            if closure_failed
            else int(name.rsplit("_P", 1)[1])
        )
        is_success_result_finalization_failure = (
            "_OUTPUT_FINALIZATION_FAILURE_" in name
        )
        business = (
            "_POST_BUSINESS_" in name
            or is_success_result_finalization_failure
        )
        matching_branches = tuple(
            item for item in H1OutputBranchV1 if name.startswith(f"{item.value}_")
        )
        if len(matching_branches) != 1:  # pragma: no cover - enum guard
            _fail("registered output case lacks one exact failure cause")
        branch = matching_branches[0]
        if prefix == len(BROKER_OUTPUT_ROLE_ORDER):
            if is_success_result_finalization_failure or closure_failed:
                phase = (
                    H1OutputCommitPhaseV1.BUSINESS_COMMITTED_OUTPUT_FINALIZATION_CLOSURE_FAILURE
                    if business
                    else H1OutputCommitPhaseV1.PRE_BUSINESS_OUTPUT_FINALIZATION_CLOSURE_FAILURE
                )
            else:
                phase = (
                    H1OutputCommitPhaseV1.BUSINESS_COMMITTED_FAILURE_BROKER_FINALIZED
                    if business
                    else H1OutputCommitPhaseV1.PRE_BUSINESS_FAILURE_BROKER_FINALIZED
                )
        else:
            phase = (
                H1OutputCommitPhaseV1.POST_BUSINESS_OUTPUT_FINALIZATION_IN_PROGRESS_FAILURE
                if business
                else H1OutputCommitPhaseV1.PRE_BUSINESS_OUTPUT_FINALIZATION_IN_PROGRESS_FAILURE
            )
        finalization_failed = (
            prefix < len(BROKER_OUTPUT_ROLE_ORDER)
            or is_success_result_finalization_failure
            or closure_failed
        )
    present = (
        ((BUSINESS_RESULT_ROLE,) if business else ())
        + BROKER_OUTPUT_ROLE_ORDER[:prefix]
    )
    present = tuple(
        role for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES if role in present
    )
    absent = tuple(
        role for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES if role not in present
    )
    return H1OutputPresenceRowV1(
        case=case,
        branch=branch,
        commit_phase=phase,
        business_result_committed=business,
        broker_prefix_count=prefix,
        present_roles=present,
        absent_roles=absent,
        output_finalization_failed=finalization_failed,
        invalidates_official_run=case is not H1OutputCaseV1.EXACT_INFEASIBLE_SUCCESS,
    )


BRANCH_PRESENCE_MATRIX = tuple(_presence_row(case) for case in H1OutputCaseV1)
if len(BRANCH_PRESENCE_MATRIX) != 72:  # pragma: no cover - static guard
    raise RuntimeError("H1 output presence matrix must have exactly 72 cases")


def presence_row_for_case_v1(case: H1OutputCaseV1 | str) -> H1OutputPresenceRowV1:
    """Return the canonical, phase-complete row for one registered case."""

    return _presence_row(case)


def business_outcome_for_case_v1(
    case: H1OutputCaseV1 | str,
) -> H1BusinessOutcomeV1 | None:
    """Return the business-owned outcome class without broker-prefix detail."""

    row = _presence_row(case)
    if not row.business_result_committed:
        return None
    if row.branch is H1OutputBranchV1.EXACT_INFEASIBLE_SUCCESS:
        return H1BusinessOutcomeV1.EXACT_INFEASIBILITY_RESULT
    if row.branch is H1OutputBranchV1.FALLBACK_CAP_EXHAUSTED:
        return H1BusinessOutcomeV1.FALLBACK_CAP_EXHAUSTED_RESULT
    return H1BusinessOutcomeV1.COMMITTED_BEFORE_LATER_FAILURE


@dataclass(frozen=True, slots=True)
class H1TypedRoleAbsenceV1:
    role: str
    owner: H1OutputOwnerV1
    kind: str
    reason: str

    def __post_init__(self) -> None:
        if self.role not in REGISTERED_OPERATIONAL_OUTPUT_ROLES:
            _fail("typed absence names an unregistered role")
        expected_owner = (
            H1OutputOwnerV1.BUSINESS
            if self.role == BUSINESS_RESULT_ROLE
            else H1OutputOwnerV1.BROKER
        )
        if self.owner is not expected_owner:
            _fail("typed absence has the wrong role owner")
        if self.kind != "NOT_COMMITTED":
            _fail("typed absence kind must be NOT_COMMITTED")
        expected_reason = (
            "BUSINESS_RESULT_NOT_COMMITTED_BEFORE_FAILURE"
            if self.role == BUSINESS_RESULT_ROLE
            else "OUTPUT_FINALIZATION_STOPPED_BEFORE_ROLE_COMMIT"
        )
        if self.reason != expected_reason:
            _fail("typed absence reason is not canonical for its owner")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "owner": self.owner.value,
            "kind": self.kind,
            "reason": self.reason,
        }


def _typed_absences(row: H1OutputPresenceRowV1) -> tuple[H1TypedRoleAbsenceV1, ...]:
    return tuple(
        H1TypedRoleAbsenceV1(
            role=role,
            owner=(
                H1OutputOwnerV1.BUSINESS
                if role == BUSINESS_RESULT_ROLE
                else H1OutputOwnerV1.BROKER
            ),
            kind="NOT_COMMITTED",
            reason=(
                "BUSINESS_RESULT_NOT_COMMITTED_BEFORE_FAILURE"
                if role == BUSINESS_RESULT_ROLE
                else "OUTPUT_FINALIZATION_STOPPED_BEFORE_ROLE_COMMIT"
            ),
        )
        for role in row.absent_roles
    )


_PROFILE_ISSUER = object()
_BUSINESS_ISSUER = object()
_BROKER_ISSUER = object()
_INPUT_ISSUER = object()
_ARTIFACT_ISSUER = object()
_SET_ISSUER = object()
_ITERATION_ISSUER = object()
_RESULT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1BranchAwareOutputProfileV1:
    schema_version: str
    role_byte_cap: int
    total_byte_cap: int
    iteration_cap: int
    issuer: InitVar[object] = field(repr=False)

    def __post_init__(self, issuer: object) -> None:
        if issuer is not _PROFILE_ISSUER:
            _fail("output profile must be issued by the module authority")
        if self.schema_version != SCHEMA_VERSION:
            _fail("output profile schema version is not canonical")
        if self.role_byte_cap != MAX_ROLE_BYTES:
            _fail("output profile role cap is not canonical")
        if self.total_byte_cap != MAX_TOTAL_BYTES:
            _fail("output profile total cap is not canonical")
        if self.iteration_cap != MAX_FIXED_POINT_ITERATIONS:
            _fail("output profile iteration cap is not canonical")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_branch_aware_output_profile.v1",
            "schema_version": self.schema_version,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "required_upstream_h1_recipe_profile_id": (
                recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1().profile_id
            ),
            "exact_upstream_recipe_and_route_context_required": True,
            "registered_output_roles": list(REGISTERED_OPERATIONAL_OUTPUT_ROLES),
            "broker_output_role_order": list(BROKER_OUTPUT_ROLE_ORDER),
            "branch_presence_matrix": [row.to_document() for row in BRANCH_PRESENCE_MATRIX],
            "role_byte_cap": self.role_byte_cap,
            "total_byte_cap": self.total_byte_cap,
            "iteration_cap": self.iteration_cap,
            "terminal_replay_count": TERMINAL_REPLAY_COUNT,
            "serializer_authority": "MODULE_OWNED_DETERMINISTIC_CANONICAL_JSON_V1",
            "opaque_renderer_callback_allowed": False,
            "business_result_owner": H1OutputOwnerV1.BUSINESS.value,
            "business_result_broker_fabrication_allowed": False,
            "manifest_self_identity_fields_allowed": False,
            "unregistered_ninth_output_allowed": False,
            "phase_split_placeholder_allowed": False,
            "production_semantic_inputs_present": False,
            "missing_production_semantic_inputs": list(
                MISSING_PRODUCTION_SEMANTIC_INPUTS
            ),
            "construction_only": True,
            "official_execution_allowed": False,
        }

    @property
    def profile_id(self) -> str:
        return _domain_content_id(PROFILE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "output_profile_id": self.profile_id}


def freeze_h1_branch_aware_output_profile_v1() -> H1BranchAwareOutputProfileV1:
    return H1BranchAwareOutputProfileV1(
        schema_version=SCHEMA_VERSION,
        role_byte_cap=MAX_ROLE_BYTES,
        total_byte_cap=MAX_TOTAL_BYTES,
        iteration_cap=MAX_FIXED_POINT_ITERATIONS,
        issuer=_PROFILE_ISSUER,
    )


@dataclass(frozen=True, slots=True)
class H1BusinessResultFixtureV1:
    outcome: H1BusinessOutcomeV1
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1
    raw_bytes: bytes
    fixture_id: str
    issuer: InitVar[object] = field(repr=False)

    def __post_init__(self, issuer: object) -> None:
        if issuer is not _BUSINESS_ISSUER:
            _fail("business result must be issued by the business fixture authority")
        _verify_business_fixture(self)


def _business_payload(
    outcome: H1BusinessOutcomeV1,
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.h1_business_result_fixture.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "role": BUSINESS_RESULT_ROLE,
        "owner": H1OutputOwnerV1.BUSINESS.value,
        "business_outcome": outcome.value,
        "recipe_context": _recipe_context(recipe),
        "issuer_kind": "ISSUER_OWNED_TYPED_FIXTURE",
        "broker_fabricated": False,
        "production_business_adapter_present": False,
        "fixture_semantics_only": True,
        "official_execution_allowed": False,
    }


def issue_h1_business_result_fixture_v1(
    *,
    outcome: H1BusinessOutcomeV1 | str,
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1,
) -> H1BusinessResultFixtureV1:
    recipe = _verify_recipe(recipe)
    try:
        outcome = H1BusinessOutcomeV1(outcome)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BranchAwareOutputContractV1Error(
            "unknown business-owned outcome"
        ) from error
    payload = _business_payload(outcome, recipe)
    fixture_id = _domain_content_id(BUSINESS_FIXTURE_DOMAIN, payload)
    raw = canonical_json_bytes({**payload, "business_result_fixture_id": fixture_id})
    return H1BusinessResultFixtureV1(
        outcome=outcome,
        recipe=recipe,
        raw_bytes=raw,
        fixture_id=fixture_id,
        issuer=_BUSINESS_ISSUER,
    )


def _verify_business_fixture(value: Any) -> H1BusinessResultFixtureV1:
    if type(value) is not H1BusinessResultFixtureV1:
        _fail("business fixture must be the exact issuer-owned type")
    recipe = _verify_recipe(value.recipe)
    if type(value.outcome) is not H1BusinessOutcomeV1:
        _fail("business fixture outcome is not exact")
    payload = _business_payload(value.outcome, recipe)
    expected_id = _domain_content_id(BUSINESS_FIXTURE_DOMAIN, payload)
    if not hmac.compare_digest(_cid(value.fixture_id, "business fixture"), expected_id):
        _fail("business fixture identity is invalid")
    expected_raw = canonical_json_bytes(
        {**payload, "business_result_fixture_id": expected_id}
    )
    if type(value.raw_bytes) is not bytes:
        _fail("business fixture bytes must be exact immutable bytes")
    if not hmac.compare_digest(value.raw_bytes, expected_raw):
        _fail("business fixture bytes are not the business-owned canonical bytes")
    return value


@dataclass(frozen=True, slots=True)
class H1BrokerOutputFixtureV1:
    case: H1OutputCaseV1
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1
    fixture_id: str
    issuer: InitVar[object] = field(repr=False)

    def __post_init__(self, issuer: object) -> None:
        if issuer is not _BROKER_ISSUER:
            _fail("broker fixture must be issued by the broker fixture authority")
        _verify_broker_fixture(self)

    def _payload(self) -> dict[str, Any]:
        row = _presence_row(self.case)
        return {
            "schema": "acfqp.h1_broker_output_fixture.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "case": row.case.value,
            "branch": row.branch.value,
            "commit_phase": row.commit_phase.value,
            "recipe_context": _recipe_context(self.recipe),
            "broker_prefix_count": row.broker_prefix_count,
            "issuer_kind": "ISSUER_OWNED_TYPED_FIXTURE",
            "owner": H1OutputOwnerV1.BROKER.value,
            "production_semantic_inputs_present": False,
            "fixture_semantics_only": True,
            "official_execution_allowed": False,
        }


def issue_h1_broker_output_fixture_v1(
    *,
    case: H1OutputCaseV1 | str,
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1,
) -> H1BrokerOutputFixtureV1:
    row = _presence_row(case)
    recipe = _verify_recipe(recipe)
    provisional = H1BrokerOutputFixtureV1.__new__(H1BrokerOutputFixtureV1)
    object.__setattr__(provisional, "case", row.case)
    object.__setattr__(provisional, "recipe", recipe)
    payload = H1BrokerOutputFixtureV1._payload(provisional)
    fixture_id = _domain_content_id(BROKER_FIXTURE_DOMAIN, payload)
    return H1BrokerOutputFixtureV1(
        case=row.case,
        recipe=recipe,
        fixture_id=fixture_id,
        issuer=_BROKER_ISSUER,
    )


def _verify_broker_fixture(value: Any) -> H1BrokerOutputFixtureV1:
    if type(value) is not H1BrokerOutputFixtureV1:
        _fail("broker fixture must be the exact issuer-owned type")
    _verify_recipe(value.recipe)
    expected = _domain_content_id(BROKER_FIXTURE_DOMAIN, value._payload())
    if not hmac.compare_digest(_cid(value.fixture_id, "broker fixture"), expected):
        _fail("broker fixture identity is invalid")
    return value


@dataclass(frozen=True, slots=True)
class H1OutputStructuralInputV1:
    case: H1OutputCaseV1
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1
    profile: H1BranchAwareOutputProfileV1
    broker_fixture: H1BrokerOutputFixtureV1
    business_fixture: H1BusinessResultFixtureV1 | None
    structural_input_id: str
    issuer: InitVar[object] = field(repr=False)

    def __post_init__(self, issuer: object) -> None:
        if issuer is not _INPUT_ISSUER:
            _fail("structural input must be issued by the input authority")
        _verify_structural_input(self)

    def _payload(self) -> dict[str, Any]:
        row = _presence_row(self.case)
        return {
            "schema": "acfqp.construction_k7_h1_branch_aware_output_input.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "output_profile_id": self.profile.profile_id,
            "recipe_context": _recipe_context(self.recipe),
            "case": row.case.value,
            "branch": row.branch.value,
            "commit_phase": row.commit_phase.value,
            "present_roles": list(row.present_roles),
            "absent_roles": [item.to_document() for item in _typed_absences(row)],
            "broker_fixture_id": self.broker_fixture.fixture_id,
            "business_fixture": (
                {
                    "kind": "PRESENT",
                    "business_result_fixture_id": self.business_fixture.fixture_id,
                }
                if self.business_fixture is not None
                else {
                    "kind": "NOT_APPLICABLE",
                    "reason": "BUSINESS_RESULT_NOT_COMMITTED_BEFORE_FAILURE",
                }
            ),
            "caller_supplied_content_ids_allowed": False,
            "caller_supplied_output_totals_allowed": False,
            "production_semantic_inputs_present": False,
            "construction_only": True,
            "official_execution_allowed": False,
        }


def freeze_h1_output_structural_input_v1(
    *,
    case: H1OutputCaseV1 | str,
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1,
    broker_fixture: H1BrokerOutputFixtureV1,
    business_fixture: H1BusinessResultFixtureV1 | None = None,
) -> H1OutputStructuralInputV1:
    row = _presence_row(case)
    recipe = _verify_recipe(recipe)
    broker = _verify_broker_fixture(broker_fixture)
    if broker.case is not row.case:
        _fail("cross-branch broker fixture transplant is forbidden")
    if broker.recipe.recipe_id != recipe.recipe_id:
        _fail("cross-recipe broker fixture transplant is forbidden")
    if row.business_result_committed:
        business = _verify_business_fixture(business_fixture)
        if business.outcome is not business_outcome_for_case_v1(row.case):
            _fail("business fixture outcome is incompatible with this route result")
        if business.recipe.recipe_id != recipe.recipe_id:
            _fail("cross-recipe business fixture transplant is forbidden")
    else:
        if business_fixture is not None:
            _fail("broker cannot fabricate or retain business output on an absent branch")
        business = None
    profile = freeze_h1_branch_aware_output_profile_v1()
    provisional = H1OutputStructuralInputV1.__new__(H1OutputStructuralInputV1)
    object.__setattr__(provisional, "case", row.case)
    object.__setattr__(provisional, "recipe", recipe)
    object.__setattr__(provisional, "profile", profile)
    object.__setattr__(provisional, "broker_fixture", broker)
    object.__setattr__(provisional, "business_fixture", business)
    payload = H1OutputStructuralInputV1._payload(provisional)
    identifier = _domain_content_id(STRUCTURAL_INPUT_DOMAIN, payload)
    return H1OutputStructuralInputV1(
        case=row.case,
        recipe=recipe,
        profile=profile,
        broker_fixture=broker,
        business_fixture=business,
        structural_input_id=identifier,
        issuer=_INPUT_ISSUER,
    )


def _verify_structural_input(value: Any) -> H1OutputStructuralInputV1:
    if type(value) is not H1OutputStructuralInputV1:
        _fail("solver accepts only one issuer-owned typed structural input")
    row = _presence_row(value.case)
    recipe = _verify_recipe(value.recipe)
    if type(value.profile) is not H1BranchAwareOutputProfileV1:
        _fail("structural input profile has the wrong type")
    canonical_profile = freeze_h1_branch_aware_output_profile_v1()
    if value.profile.to_document() != canonical_profile.to_document():
        _fail("structural input profile is not the frozen profile")
    broker = _verify_broker_fixture(value.broker_fixture)
    if broker.case is not row.case:
        _fail("structural input has a cross-branch broker fixture")
    if broker.recipe.recipe_id != recipe.recipe_id:
        _fail("structural input has a cross-recipe broker fixture")
    if row.business_result_committed:
        business = _verify_business_fixture(value.business_fixture)
        if business.outcome is not business_outcome_for_case_v1(row.case):
            _fail("structural input has an incompatible business outcome")
        if business.recipe.recipe_id != recipe.recipe_id:
            _fail("structural input has a cross-recipe business fixture")
    elif value.business_fixture is not None:
        _fail("business-result absence cannot contain a business fixture")
    expected = _domain_content_id(STRUCTURAL_INPUT_DOMAIN, value._payload())
    if not hmac.compare_digest(
        _cid(value.structural_input_id, "structural input"), expected
    ):
        _fail("structural input identity is invalid")
    return value


def _owner_for_role(role: str) -> H1OutputOwnerV1:
    return (
        H1OutputOwnerV1.BUSINESS
        if role == BUSINESS_RESULT_ROLE
        else H1OutputOwnerV1.BROKER
    )


def _serialize_business_result_v1(source: H1OutputStructuralInputV1) -> bytes:
    if source.business_fixture is None:
        _fail("broker attempted to fabricate a missing business result")
    return _verify_business_fixture(source.business_fixture).raw_bytes


def _serialize_broker_role_v1(
    source: H1OutputStructuralInputV1,
    role: str,
) -> bytes:
    if role not in BROKER_OUTPUT_ROLE_ORDER[:-1]:
        _fail("non-manifest broker serializer received the wrong role")
    row = _presence_row(source.case)
    terminal_code = {
        H1OutputBranchV1.EXACT_INFEASIBLE_SUCCESS: "FULL_GROUND_EXACT_INFEASIBLE",
        H1OutputBranchV1.FALLBACK_CAP_EXHAUSTED: "FALLBACK_CAP_EXHAUSTED",
        H1OutputBranchV1.PROTOCOL_FAILURE: "PROTOCOL_FAILURE",
        H1OutputBranchV1.INTEGRITY_FAILURE: "INTEGRITY_FAILURE",
        H1OutputBranchV1.AMBIGUOUS_NATIVE_LAUNCH: "PROTOCOL_FAILURE",
        H1OutputBranchV1.H1_BUSINESS_ADAPTER_FAILURE: "PROTOCOL_FAILURE",
    }[row.branch]
    document = {
        "schema": f"acfqp.h1_{role.lower()}_fixture.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "role": role,
        "owner": H1OutputOwnerV1.BROKER.value,
        "primary_terminal_cause": row.branch.value,
        "business_result_committed_before_finalization": (
            row.business_result_committed
        ),
        "recipe_context": _recipe_context(source.recipe),
        "terminal_code_fixture": terminal_code,
        "fixture_semantics_only": True,
        "production_semantic_authority": False,
        "official_execution_allowed": False,
    }
    return canonical_json_bytes(document)


@dataclass(frozen=True, slots=True)
class H1RenderedRoleArtifactV1:
    role: str
    owner: H1OutputOwnerV1
    raw_bytes: bytes
    sha256: str
    byte_count: int
    artifact_id: str
    issuer: InitVar[object] = field(repr=False)

    def __post_init__(self, issuer: object) -> None:
        if issuer is not _ARTIFACT_ISSUER:
            _fail("rendered role artifact must be issued by the serializer")
        if self.role not in REGISTERED_OPERATIONAL_OUTPUT_ROLES:
            _fail("rendered artifact has an unregistered role")
        if self.owner is not _owner_for_role(self.role):
            _fail("rendered artifact has the wrong owner")
        _canonical_object(self.raw_bytes, f"{self.role} bytes")
        if self.sha256 != _hash(self.raw_bytes):
            _fail("rendered artifact SHA-256 is invalid")
        _exact_int(self.byte_count, "rendered artifact extent")
        if self.byte_count != len(self.raw_bytes):
            _fail("rendered artifact extent is invalid")
        if self.byte_count > MAX_ROLE_BYTES:
            _fail("rendered artifact exceeds its frozen role cap")
        expected = _domain_content_id(
            ROLE_ARTIFACT_DOMAIN,
            {
                "schema": "acfqp.h1_rendered_role_artifact.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "role": self.role,
                "owner": self.owner.value,
                "sha256": self.sha256,
                "byte_count": self.byte_count,
            },
        )
        if not hmac.compare_digest(_cid(self.artifact_id, "role artifact"), expected):
            _fail("rendered artifact identity is invalid")

    def descriptor(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "owner": self.owner.value,
            "artifact_id": self.artifact_id,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
        }


def _freeze_artifact(role: str, raw: bytes) -> H1RenderedRoleArtifactV1:
    owner = _owner_for_role(role)
    digest = _hash(raw)
    extent = len(raw)
    identifier = _domain_content_id(
        ROLE_ARTIFACT_DOMAIN,
        {
            "schema": "acfqp.h1_rendered_role_artifact.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "role": role,
            "owner": owner.value,
            "sha256": digest,
            "byte_count": extent,
        },
    )
    return H1RenderedRoleArtifactV1(
        role=role,
        owner=owner,
        raw_bytes=raw,
        sha256=digest,
        byte_count=extent,
        artifact_id=identifier,
        issuer=_ARTIFACT_ISSUER,
    )


_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "role",
        "owner",
        "primary_terminal_cause",
        "business_result_committed_before_finalization",
        "recipe_context",
        "candidate_output_bytes",
        "present_non_manifest_roles",
        "absent_roles",
        "registered_role_count",
        "durable_output_count",
        "manifest_self_identity_fields_present",
        "unregistered_ninth_output_present",
        "production_semantic_authority",
        "official_execution_allowed",
    }
)


def _serialize_output_manifest_v1(
    source: H1OutputStructuralInputV1,
    candidate_output_bytes: int,
    present_non_manifest: tuple[H1RenderedRoleArtifactV1, ...],
    absences: tuple[H1TypedRoleAbsenceV1, ...],
) -> bytes:
    _exact_int(candidate_output_bytes, "candidate output bytes")
    row = _presence_row(source.case)
    expected_non_manifest = tuple(
        role for role in row.present_roles if role != OUTPUT_MANIFEST_ROLE
    )
    if tuple(item.role for item in present_non_manifest) != expected_non_manifest:
        _fail("manifest received a reordered or incomplete non-manifest role set")
    if tuple(item.role for item in absences) != row.absent_roles:
        _fail("manifest received the wrong typed absence set")
    document = {
        "schema": "acfqp.h1_output_manifest_fixture.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "role": OUTPUT_MANIFEST_ROLE,
        "owner": H1OutputOwnerV1.BROKER.value,
        "primary_terminal_cause": row.branch.value,
        "business_result_committed_before_finalization": (
            row.business_result_committed
        ),
        "recipe_context": _recipe_context(source.recipe),
        "candidate_output_bytes": candidate_output_bytes,
        "present_non_manifest_roles": [
            item.descriptor() for item in present_non_manifest
        ],
        "absent_roles": [item.to_document() for item in absences],
        "registered_role_count": len(REGISTERED_OPERATIONAL_OUTPUT_ROLES),
        "durable_output_count": len(row.present_roles),
        "manifest_self_identity_fields_present": False,
        "unregistered_ninth_output_present": False,
        "production_semantic_authority": False,
        "official_execution_allowed": False,
    }
    if set(document) != _MANIFEST_FIELDS:
        _fail("output manifest serializer changed its exact field set")
    return canonical_json_bytes(document)


@dataclass(frozen=True, slots=True)
class H1RenderedArtifactSetV1:
    structural_input: H1OutputStructuralInputV1
    candidate_output_bytes: int
    artifacts: tuple[H1RenderedRoleArtifactV1, ...]
    absences: tuple[H1TypedRoleAbsenceV1, ...]
    actual_output_bytes: int
    artifact_set_id: str
    issuer: InitVar[object] = field(repr=False)

    def __post_init__(self, issuer: object) -> None:
        if issuer is not _SET_ISSUER:
            _fail("artifact set must be issued by the module renderer")
        _verify_artifact_set(self)

    def _payload(self) -> dict[str, Any]:
        row = _presence_row(self.structural_input.case)
        return {
            "schema": "acfqp.h1_rendered_artifact_set.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "structural_input_id": self.structural_input.structural_input_id,
            "case": row.case.value,
            "branch": row.branch.value,
            "commit_phase": row.commit_phase.value,
            "candidate_output_bytes": self.candidate_output_bytes,
            "present_artifacts": [item.descriptor() for item in self.artifacts],
            "absent_roles": [item.to_document() for item in self.absences],
            "actual_output_bytes": self.actual_output_bytes,
            "registered_role_count": len(REGISTERED_OPERATIONAL_OUTPUT_ROLES),
            "durable_output_count": len(self.artifacts),
            "hidden_or_wrapper_output_count": 0,
            "construction_record_is_operational_output": False,
        }


def _artifact_set_identity(value: H1RenderedArtifactSetV1) -> str:
    return _domain_content_id(ARTIFACT_SET_DOMAIN, value._payload())


def _render_candidate_once_v1(
    source: H1OutputStructuralInputV1,
    candidate_output_bytes: int,
) -> H1RenderedArtifactSetV1:
    source = _verify_structural_input(source)
    _exact_int(candidate_output_bytes, "candidate output bytes")
    if candidate_output_bytes > source.profile.total_byte_cap:
        _fail("candidate output bytes exceed the frozen total cap")
    row = _presence_row(source.case)
    absences = _typed_absences(row)
    rendered: list[H1RenderedRoleArtifactV1] = []
    for role in row.present_roles:
        if role == OUTPUT_MANIFEST_ROLE:
            raw = _serialize_output_manifest_v1(
                source,
                candidate_output_bytes,
                tuple(rendered),
                absences,
            )
        elif role == BUSINESS_RESULT_ROLE:
            raw = _serialize_business_result_v1(source)
        else:
            raw = _serialize_broker_role_v1(source, role)
        rendered.append(_freeze_artifact(role, raw))
    actual = sum(item.byte_count for item in rendered)
    if actual > source.profile.total_byte_cap:
        _fail("rendered output exceeds the frozen total cap")
    provisional = H1RenderedArtifactSetV1.__new__(H1RenderedArtifactSetV1)
    object.__setattr__(provisional, "structural_input", source)
    object.__setattr__(provisional, "candidate_output_bytes", candidate_output_bytes)
    object.__setattr__(provisional, "artifacts", tuple(rendered))
    object.__setattr__(provisional, "absences", absences)
    object.__setattr__(provisional, "actual_output_bytes", actual)
    identifier = _artifact_set_identity(provisional)
    return H1RenderedArtifactSetV1(
        structural_input=source,
        candidate_output_bytes=candidate_output_bytes,
        artifacts=tuple(rendered),
        absences=absences,
        actual_output_bytes=actual,
        artifact_set_id=identifier,
        issuer=_SET_ISSUER,
    )


def _verify_artifact_set(value: Any) -> H1RenderedArtifactSetV1:
    if type(value) is not H1RenderedArtifactSetV1:
        _fail("artifact set has the wrong type")
    source = _verify_structural_input(value.structural_input)
    _exact_int(value.candidate_output_bytes, "candidate output bytes")
    if value.candidate_output_bytes > source.profile.total_byte_cap:
        _fail("artifact-set candidate exceeds the frozen total cap")
    row = _presence_row(source.case)
    if type(value.artifacts) is not tuple or any(
        type(item) is not H1RenderedRoleArtifactV1 for item in value.artifacts
    ):
        _fail("artifact set must contain exact rendered-role tuples")
    if tuple(item.role for item in value.artifacts) != row.present_roles:
        _fail("artifact set has a reordered, missing, or ninth role")
    expected_absences = _typed_absences(row)
    if value.absences != expected_absences:
        _fail("artifact set does not preserve the exact typed absent subset")
    expected_raw_by_role: dict[str, bytes] = {}
    preceding: list[H1RenderedRoleArtifactV1] = []
    for item in value.artifacts:
        if item.role == BUSINESS_RESULT_ROLE:
            expected_raw = _serialize_business_result_v1(source)
        elif item.role == OUTPUT_MANIFEST_ROLE:
            expected_raw = _serialize_output_manifest_v1(
                source,
                value.candidate_output_bytes,
                tuple(preceding),
                expected_absences,
            )
            manifest = _canonical_object(item.raw_bytes, "output manifest")
            if set(manifest) != _MANIFEST_FIELDS:
                _fail("output manifest has missing, extra, or self-reference fields")
            if manifest["manifest_self_identity_fields_present"] is not False:
                _fail("output manifest claims a self identity")
            if manifest["unregistered_ninth_output_present"] is not False:
                _fail("output manifest claims an unregistered ninth output")
            forbidden = {
                "output_manifest_id",
                "manifest_id",
                "manifest_sha256",
                "manifest_byte_count",
                "own_artifact_id",
                "own_sha256",
            }
            if forbidden & set(manifest):
                _fail("output manifest contains its own identity or extent")
        else:
            expected_raw = _serialize_broker_role_v1(source, item.role)
        expected_raw_by_role[item.role] = expected_raw
        if not hmac.compare_digest(item.raw_bytes, expected_raw):
            _fail("rendered role bytes differ from the module-owned serializer")
        expected_artifact = _freeze_artifact(item.role, expected_raw)
        if item.descriptor() != expected_artifact.descriptor():
            _fail("rendered role identity/hash/extent is invalid")
        preceding.append(item)
    expected_total = sum(len(raw) for raw in expected_raw_by_role.values())
    if value.actual_output_bytes != expected_total:
        _fail("artifact-set actual total is not the exact role-byte sum")
    _exact_int(value.actual_output_bytes, "artifact-set actual output bytes")
    if value.actual_output_bytes > source.profile.total_byte_cap:
        _fail("artifact-set total exceeds the frozen cap")
    expected_id = _artifact_set_identity(value)
    if not hmac.compare_digest(_cid(value.artifact_set_id, "artifact set"), expected_id):
        _fail("artifact-set identity is invalid")
    return value


def verify_h1_rendered_artifact_set_v1(
    value: H1RenderedArtifactSetV1,
) -> H1RenderedArtifactSetV1:
    """Replay exact serializers and the branch presence matrix."""

    return _verify_artifact_set(value)


@dataclass(frozen=True, slots=True)
class H1OutputFixedPointIterationV1:
    iteration_index: int
    candidate_output_bytes: int
    observed_output_bytes: int
    artifact_set_id: str
    converged: bool
    iteration_id: str
    issuer: InitVar[object] = field(repr=False)

    def __post_init__(self, issuer: object) -> None:
        if issuer is not _ITERATION_ISSUER:
            _fail("fixed-point iteration must be issued by the solver")
        _exact_int(self.iteration_index, "iteration index", minimum=1)
        _exact_int(self.candidate_output_bytes, "iteration candidate")
        _exact_int(self.observed_output_bytes, "iteration observation")
        _cid(self.artifact_set_id, "iteration artifact set")
        if type(self.converged) is not bool:
            _fail("iteration convergence flag must be exact bool")
        expected = _domain_content_id(ITERATION_DOMAIN, self._payload())
        if not hmac.compare_digest(_cid(self.iteration_id, "iteration"), expected):
            _fail("fixed-point iteration identity is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.h1_output_fixed_point_iteration.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "iteration_index": self.iteration_index,
            "candidate_output_bytes": self.candidate_output_bytes,
            "observed_output_bytes": self.observed_output_bytes,
            "artifact_set_id": self.artifact_set_id,
            "converged": self.converged,
        }


def _freeze_iteration(
    index: int,
    candidate: int,
    rendered: H1RenderedArtifactSetV1,
) -> H1OutputFixedPointIterationV1:
    provisional = H1OutputFixedPointIterationV1.__new__(
        H1OutputFixedPointIterationV1
    )
    object.__setattr__(provisional, "iteration_index", index)
    object.__setattr__(provisional, "candidate_output_bytes", candidate)
    object.__setattr__(provisional, "observed_output_bytes", rendered.actual_output_bytes)
    object.__setattr__(provisional, "artifact_set_id", rendered.artifact_set_id)
    object.__setattr__(
        provisional, "converged", candidate == rendered.actual_output_bytes
    )
    identifier = _domain_content_id(ITERATION_DOMAIN, provisional._payload())
    return H1OutputFixedPointIterationV1(
        iteration_index=index,
        candidate_output_bytes=candidate,
        observed_output_bytes=rendered.actual_output_bytes,
        artifact_set_id=rendered.artifact_set_id,
        converged=candidate == rendered.actual_output_bytes,
        iteration_id=identifier,
        issuer=_ITERATION_ISSUER,
    )


@dataclass(frozen=True, slots=True)
class H1OutputFixedPointResultV1:
    structural_input: H1OutputStructuralInputV1
    iterations: tuple[H1OutputFixedPointIterationV1, ...]
    final_artifact_set: H1RenderedArtifactSetV1
    terminal_replay_artifact_set_ids: tuple[str, ...]
    exact_fixed_point: bool
    result_id: str
    issuer: InitVar[object] = field(repr=False)

    def __post_init__(self, issuer: object) -> None:
        if issuer is not _RESULT_ISSUER:
            _fail("fixed-point result must be issued by the solver")
        _verify_result_structure(self)

    def _payload(self) -> dict[str, Any]:
        row = _presence_row(self.structural_input.case)
        return {
            "schema": "acfqp.h1_branch_aware_output_fixed_point_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "structural_input_id": self.structural_input.structural_input_id,
            "case": row.case.value,
            "branch": row.branch.value,
            "commit_phase": row.commit_phase.value,
            "present_roles": list(row.present_roles),
            "absent_roles": [item.to_document() for item in self.final_artifact_set.absences],
            "iteration_ids": [item.iteration_id for item in self.iterations],
            "final_artifact_set_id": self.final_artifact_set.artifact_set_id,
            "candidate_output_bytes": self.final_artifact_set.candidate_output_bytes,
            "actual_output_bytes": self.final_artifact_set.actual_output_bytes,
            "terminal_replay_artifact_set_ids": list(
                self.terminal_replay_artifact_set_ids
            ),
            "exact_fixed_point": self.exact_fixed_point,
            "branch_presence_exact": True,
            "module_owned_serializer_replayed": True,
            "hidden_or_wrapper_output_count": 0,
            "construction_record_is_operational_output": False,
            "output_finalization_failed": row.output_finalization_failed,
            "invalidates_official_run": row.invalidates_official_run,
            "production_semantic_inputs_present": False,
            "formal_v7_route_authority_present": False,
            "numeric_aggregate_candidate_issued": False,
            "counter_completeness_gate_run": False,
            "workload_economics_gate_run": False,
            "official_scalar_cost": None,
            "official_n_break_even": None,
            "official_execution_allowed": False,
        }


def _verify_result_structure(value: Any) -> H1OutputFixedPointResultV1:
    if type(value) is not H1OutputFixedPointResultV1:
        _fail("fixed-point result has the wrong type")
    source = _verify_structural_input(value.structural_input)
    if type(value.iterations) is not tuple or not value.iterations:
        _fail("fixed-point result must preserve nonempty exact iterations")
    if len(value.iterations) > source.profile.iteration_cap:
        _fail("fixed-point result exceeds the frozen iteration cap")
    if value.iterations[0].candidate_output_bytes != 0:
        _fail("fixed-point iteration sequence must start from candidate zero")
    previous_candidate = -1
    previous_observed: int | None = None
    for expected_index, item in enumerate(value.iterations, 1):
        if type(item) is not H1OutputFixedPointIterationV1:
            _fail("fixed-point result contains a malformed iteration")
        if item.iteration_index != expected_index:
            _fail("fixed-point iteration indices are not contiguous")
        if item.candidate_output_bytes <= previous_candidate and expected_index > 1:
            _fail("fixed-point candidates are not strictly monotone before convergence")
        if previous_observed is not None and item.candidate_output_bytes != previous_observed:
            _fail("fixed-point iteration does not consume the preceding observation")
        replay_a = _render_candidate_once_v1(source, item.candidate_output_bytes)
        replay_b = _render_candidate_once_v1(source, item.candidate_output_bytes)
        if replay_a.artifact_set_id != replay_b.artifact_set_id:
            _fail("fixed-point iteration replay is nondeterministic")
        if (
            item.observed_output_bytes != replay_a.actual_output_bytes
            or item.artifact_set_id != replay_a.artifact_set_id
            or item.converged
            is not (item.candidate_output_bytes == replay_a.actual_output_bytes)
        ):
            _fail("fixed-point iteration does not match exact serializer replay")
        if expected_index < len(value.iterations) and item.converged:
            _fail("fixed-point iteration sequence continues after convergence")
        previous_candidate = item.candidate_output_bytes
        previous_observed = item.observed_output_bytes
        expected_iteration_id = _domain_content_id(ITERATION_DOMAIN, item._payload())
        if item.iteration_id != expected_iteration_id:
            _fail("fixed-point iteration identity changed")
    final_set = _verify_artifact_set(value.final_artifact_set)
    final_iteration = value.iterations[-1]
    if final_iteration.artifact_set_id != final_set.artifact_set_id:
        _fail("final iteration does not bind the final artifact set")
    if not final_iteration.converged:
        _fail("fixed-point result terminates on a nonconverged iteration")
    if final_set.candidate_output_bytes != final_set.actual_output_bytes:
        _fail("fixed-point result candidate differs from actual output bytes")
    if value.exact_fixed_point is not True:
        _fail("fixed-point result must assert exact equality")
    if (
        type(value.terminal_replay_artifact_set_ids) is not tuple
        or len(value.terminal_replay_artifact_set_ids) != TERMINAL_REPLAY_COUNT
        or any(item != final_set.artifact_set_id for item in value.terminal_replay_artifact_set_ids)
    ):
        _fail("terminal deterministic replays do not equal the fixed artifact set")
    expected = _domain_content_id(RESULT_DOMAIN, value._payload())
    if not hmac.compare_digest(_cid(value.result_id, "fixed-point result"), expected):
        _fail("fixed-point result identity is invalid")
    return value


def solve_h1_branch_aware_output_fixed_point_v1(
    source: H1OutputStructuralInputV1,
) -> H1OutputFixedPointResultV1:
    """Solve the exact branch subset without accepting a renderer or totals."""

    source = _verify_structural_input(source)
    candidate = 0
    iterations: list[H1OutputFixedPointIterationV1] = []
    final_set: H1RenderedArtifactSetV1 | None = None
    for index in range(1, source.profile.iteration_cap + 1):
        first = _render_candidate_once_v1(source, candidate)
        second = _render_candidate_once_v1(source, candidate)
        if (
            first.artifact_set_id != second.artifact_set_id
            or tuple(item.raw_bytes for item in first.artifacts)
            != tuple(item.raw_bytes for item in second.artifacts)
        ):
            _fail("module-owned output serializer is nondeterministic")
        observed = first.actual_output_bytes
        if observed < candidate:
            _fail("output-byte fixed point violated monotonicity")
        iteration = _freeze_iteration(index, candidate, first)
        iterations.append(iteration)
        if observed == candidate:
            final_set = first
            break
        candidate = observed
    if final_set is None:
        _fail("output-byte fixed point did not converge within the frozen cap")
    terminal_replays = tuple(
        _render_candidate_once_v1(source, final_set.candidate_output_bytes)
        for _ in range(TERMINAL_REPLAY_COUNT)
    )
    if any(
        item.artifact_set_id != final_set.artifact_set_id
        or tuple(artifact.raw_bytes for artifact in item.artifacts)
        != tuple(artifact.raw_bytes for artifact in final_set.artifacts)
        for item in terminal_replays
    ):
        _fail("terminal fixed-point replay is nondeterministic")
    replay_ids = tuple(item.artifact_set_id for item in terminal_replays)
    provisional = H1OutputFixedPointResultV1.__new__(H1OutputFixedPointResultV1)
    object.__setattr__(provisional, "structural_input", source)
    object.__setattr__(provisional, "iterations", tuple(iterations))
    object.__setattr__(provisional, "final_artifact_set", final_set)
    object.__setattr__(provisional, "terminal_replay_artifact_set_ids", replay_ids)
    object.__setattr__(provisional, "exact_fixed_point", True)
    identifier = _domain_content_id(RESULT_DOMAIN, provisional._payload())
    return H1OutputFixedPointResultV1(
        structural_input=source,
        iterations=tuple(iterations),
        final_artifact_set=final_set,
        terminal_replay_artifact_set_ids=replay_ids,
        exact_fixed_point=True,
        result_id=identifier,
        issuer=_RESULT_ISSUER,
    )


def replay_h1_branch_aware_output_fixed_point_v1(
    result: H1OutputFixedPointResultV1,
) -> H1OutputFixedPointResultV1:
    """Independently rerun the structural solver and require byte equality."""

    original = _verify_result_structure(result)
    replay = solve_h1_branch_aware_output_fixed_point_v1(original.structural_input)
    if replay.result_id != original.result_id:
        _fail("fixed-point replay result identity differs")
    if tuple(item.raw_bytes for item in replay.final_artifact_set.artifacts) != tuple(
        item.raw_bytes for item in original.final_artifact_set.artifacts
    ):
        _fail("fixed-point replay bytes differ")
    return replay


def verify_h1_output_role_bytes_v1(
    *,
    recipe_bytes: bytes,
    preexecution_candidate_bytes: bytes,
    case: H1OutputCaseV1 | str,
    ordered_role_bytes: tuple[tuple[str, bytes], ...],
) -> H1RenderedArtifactSetV1:
    """Independently replay an exact ordered role-byte set.

    This boundary accepts no issuer object, caller content ID, renderer or
    output total.  It reconstructs the Contract 2.0.50 recipe from canonical
    recipe/preexecution bytes, derives the expected profile and owner fixtures,
    and reruns the branch fixed point.  The returned object is an in-memory
    verification record, never a ninth durable output.
    """

    try:
        recipe = recipe_v1.verify_h1_direct_fallback_two_role_recipe_bytes_v1(
            raw=recipe_bytes,
            preexecution_candidate_bytes=preexecution_candidate_bytes,
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BranchAwareOutputContractV1Error(
            "raw-byte verifier rejected the upstream H1 recipe/context"
        ) from error
    row = _presence_row(case)
    if type(ordered_role_bytes) is not tuple or any(
        type(item) is not tuple
        or len(item) != 2
        or type(item[0]) is not str
        or type(item[1]) is not bytes
        for item in ordered_role_bytes
    ):
        _fail("raw-byte verifier requires exact ordered (role, bytes) tuples")
    if tuple(role for role, _ in ordered_role_bytes) != row.present_roles:
        _fail("raw-byte verifier received reordered, missing, or ninth roles")
    broker = issue_h1_broker_output_fixture_v1(case=row.case, recipe=recipe)
    business = (
        issue_h1_business_result_fixture_v1(
            outcome=business_outcome_for_case_v1(row.case), recipe=recipe
        )
        if row.business_result_committed
        else None
    )
    source = freeze_h1_output_structural_input_v1(
        case=row.case,
        recipe=recipe,
        broker_fixture=broker,
        business_fixture=business,
    )
    supplied = dict(ordered_role_bytes)
    if OUTPUT_MANIFEST_ROLE in supplied:
        manifest = _canonical_object(supplied[OUTPUT_MANIFEST_ROLE], "output manifest")
        if set(manifest) != _MANIFEST_FIELDS:
            _fail("raw output manifest has missing, extra, or self-reference fields")
        candidate = _exact_int(
            manifest.get("candidate_output_bytes"), "manifest candidate output bytes"
        )
    else:
        candidate = sum(len(raw) for _, raw in ordered_role_bytes)
    if candidate > source.profile.total_byte_cap:
        _fail("raw-byte candidate exceeds the frozen total cap")
    replay = _render_candidate_once_v1(source, candidate)
    if tuple((item.role, item.raw_bytes) for item in replay.artifacts) != ordered_role_bytes:
        _fail("raw role bytes differ from exact owner serializers")
    if replay.actual_output_bytes != candidate:
        _fail("raw role bytes do not satisfy exact fixed-point equality")
    solved = solve_h1_branch_aware_output_fixed_point_v1(source)
    if solved.final_artifact_set.artifact_set_id != replay.artifact_set_id:
        _fail("raw role-byte set differs from deterministic fixed-point replay")
    return replay


def parse_output_manifest_v1(
    artifact: H1RenderedRoleArtifactV1,
    *,
    expected_recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1,
) -> dict[str, Any]:
    """Return a checked manifest document for focused construction audits."""

    expected_recipe = _verify_recipe(expected_recipe)
    if type(artifact) is not H1RenderedRoleArtifactV1 or artifact.role != OUTPUT_MANIFEST_ROLE:
        _fail("artifact is not the registered output manifest")
    expected_artifact = _freeze_artifact(OUTPUT_MANIFEST_ROLE, artifact.raw_bytes)
    if artifact.descriptor() != expected_artifact.descriptor():
        _fail("output manifest artifact hash, extent, or identity is invalid")
    document = _canonical_object(artifact.raw_bytes, "output manifest")
    if set(document) != _MANIFEST_FIELDS:
        _fail("output manifest has missing or extra fields")
    if (
        document["schema"] != "acfqp.h1_output_manifest_fixture.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["role"] != OUTPUT_MANIFEST_ROLE
        or document["owner"] != H1OutputOwnerV1.BROKER.value
        or document["manifest_self_identity_fields_present"] is not False
        or document["unregistered_ninth_output_present"] is not False
        or document["production_semantic_authority"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _fail("output manifest violates owner, self-reference, or lock invariants")
    try:
        branch = H1OutputBranchV1(document["primary_terminal_cause"])
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BranchAwareOutputContractV1Error(
            "output manifest primary terminal cause is unknown"
        ) from error
    business_committed = document[
        "business_result_committed_before_finalization"
    ]
    if type(business_committed) is not bool:
        _fail("output manifest business-commit flag must be exact bool")
    if branch in (
        H1OutputBranchV1.EXACT_INFEASIBLE_SUCCESS,
        H1OutputBranchV1.FALLBACK_CAP_EXHAUSTED,
    ) and not business_committed:
        _fail("business-result terminal cause lacks its committed result")
    expected_present_roles = (
        ((BUSINESS_RESULT_ROLE,) if business_committed else ())
        + BROKER_OUTPUT_ROLE_ORDER[:-1]
    )
    expected_present_roles = tuple(
        role
        for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES
        if role in expected_present_roles
    )
    expected_absent_roles = tuple(
        role
        for role in REGISTERED_OPERATIONAL_OUTPUT_ROLES
        if role not in (*expected_present_roles, OUTPUT_MANIFEST_ROLE)
    )
    if (
        document["registered_role_count"] != len(REGISTERED_OPERATIONAL_OUTPUT_ROLES)
        or type(document["registered_role_count"]) is not int
        or document["durable_output_count"] != len(expected_present_roles) + 1
        or type(document["durable_output_count"]) is not int
    ):
        _fail("output manifest branch or role cardinality is invalid")
    candidate = _exact_int(
        document["candidate_output_bytes"], "manifest candidate output bytes"
    )
    if candidate > MAX_TOTAL_BYTES:
        _fail("output manifest candidate exceeds the frozen total cap")
    recipe_context = document["recipe_context"]
    if type(recipe_context) is not dict or set(recipe_context) != _RECIPE_CONTEXT_FIELDS:
        _fail("output manifest recipe context fields must be exact")
    if recipe_context["upstream_h1_recipe_profile_id"] != (
        recipe_v1.official_h1_direct_fallback_two_role_recipe_profile_v1().profile_id
    ):
        _fail("output manifest binds the wrong upstream recipe profile")
    if recipe_context != _recipe_context(expected_recipe):
        _fail("output manifest differs from the expected exact recipe context")
    for field_name, value in recipe_context.items():
        if field_name.endswith("_id") or field_name == "BuildEpoch_id":
            _cid(value, f"manifest recipe context {field_name}")
    present = document["present_non_manifest_roles"]
    if type(present) is not list or tuple(
        item.get("role") if type(item) is dict else None for item in present
    ) != expected_present_roles:
        _fail("output manifest present-role descriptors are reordered or incomplete")
    descriptor_fields = {"role", "owner", "artifact_id", "sha256", "byte_count"}
    for item in present:
        if set(item) != descriptor_fields:
            _fail("output manifest role descriptor fields are not exact")
        role = item["role"]
        expected_owner = _owner_for_role(role)
        if item["owner"] != expected_owner.value:
            _fail("output manifest role descriptor has the wrong owner")
        extent = _exact_int(item["byte_count"], "manifest role extent")
        if extent > MAX_ROLE_BYTES:
            _fail("output manifest role descriptor exceeds the frozen cap")
        digest = item["sha256"]
        if (
            type(digest) is not str
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
        ):
            _fail("output manifest role descriptor SHA-256 is invalid")
        expected_id = _domain_content_id(
            ROLE_ARTIFACT_DOMAIN,
            {
                "schema": "acfqp.h1_rendered_role_artifact.v1",
                "schema_version": SCHEMA_VERSION,
                "profile_key": PROFILE_KEY,
                "role": role,
                "owner": expected_owner.value,
                "sha256": digest,
                "byte_count": extent,
            },
        )
        if not hmac.compare_digest(
            _cid(item["artifact_id"], "manifest role artifact"), expected_id
        ):
            _fail("output manifest role artifact identity is invalid")
    expected_absences = [
        H1TypedRoleAbsenceV1(
            role=role,
            owner=_owner_for_role(role),
            kind="NOT_COMMITTED",
            reason=(
                "BUSINESS_RESULT_NOT_COMMITTED_BEFORE_FAILURE"
                if role == BUSINESS_RESULT_ROLE
                else "OUTPUT_FINALIZATION_STOPPED_BEFORE_ROLE_COMMIT"
            ),
        ).to_document()
        for role in expected_absent_roles
    ]
    if document["absent_roles"] != expected_absences:
        _fail("output manifest typed absent roles are invalid")
    return document
