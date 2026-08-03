"""Construction-only H1 business request and result candidate schemas.

The retained fixture can be frozen only against explicit nonauthoritative
current-access and formal-V7 decision candidates.  It cannot satisfy the
future production authority boundary.  The Contract 2.0.52 candidate and
Contract 2.0.50 upper/decision are rejected explicitly.  The result binds the
source-owned V4 transcript's execution fingerprint to the exact search result
while keeping the search helper's legacy WorkVector diagnostic-only.

This module launches no process and authorizes no route execution.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from fractions import Fraction
import hashlib
import hmac
from typing import Any, Mapping, NoReturn, Protocol, runtime_checkable

from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_accounting_route_segment_v4 as route_v4
from acfqp import construction_k7_h1_direct_fallback_two_role_recipe_v1 as recipe_v1
from acfqp import construction_k7_h1_production_current_identity_v1 as current_v1
from acfqp import phase3e_fallback_owned_v3 as owned_v3
from acfqp.core import QuerySpec
from acfqp.domains.g2048 import G2048Kernel
from acfqp.phase3e_exact_infeasibility_durable_proof_v1 import (
    DurableExactInfeasibilityIdentityV1,
    DurableProofVerificationOutcomeV1,
    verify_phase3e_exact_infeasibility_durable_proof_bytes_v1,
)
from acfqp.phase3e_fallback_v1 import (
    GroundFallbackExecutionV1,
    GroundFallbackOutcome,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_BUSINESS_ADAPTER_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_FORMAL_V7_DECISION_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_BUSINESS_REQUEST_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_BUSINESS_RESULT_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_SEARCH_SEMANTICS_BRIDGE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.55"
PROFILE_KEY = "construction_k7_h1_business_adapter_v1"
CONSTRUCTION_ONLY = True
PRODUCTION_REQUEST_SCHEMA_PRESENT = True
PRODUCTION_REQUEST_AUTHORITY_PRESENT = False
PRODUCTION_CURRENT_ACCESS_AUTHORITY_PRESENT = False
FORMAL_V7_ROUTE_AUTHORITY_PRESENT = False
PROCESS_RUNTIME_WIRED = False
OFFICIAL_EXECUTION_ALLOWED = False
OFFICIAL_SCALAR_COST = None
OFFICIAL_N_BREAK_EVEN = None
COUNTER_COMPLETENESS_GATE_STATUS = "COUNTER_COMPLETENESS_GATE_NOT_RUN"
WORKLOAD_ECONOMICS_GATE_STATUS = "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
SAMPLE_EFFICIENCY_GATE_STATUS = "SAMPLE_EFFICIENCY_GATE_NOT_RUN"

PROFILE_DOMAIN = CONSTRUCTION_K7_H1_BUSINESS_ADAPTER_PROFILE_V1_DOMAIN
CURRENT_CANDIDATE_DOMAIN = CONSTRUCTION_K7_H1_CURRENT_ACCESS_CANDIDATE_V1_DOMAIN
FORMAL_CANDIDATE_DOMAIN = CONSTRUCTION_K7_H1_FORMAL_V7_DECISION_CANDIDATE_V1_DOMAIN
SEARCH_SEMANTICS_BRIDGE_DOMAIN = (
    CONSTRUCTION_K7_H1_SEARCH_SEMANTICS_BRIDGE_V1_DOMAIN
)
REQUEST_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_BUSINESS_REQUEST_CANDIDATE_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_BUSINESS_RESULT_CANDIDATE_V1_DOMAIN
REQUESTED_PHASE3E_DOMAIN_TAGS = (
    PROFILE_DOMAIN,
    CURRENT_CANDIDATE_DOMAIN,
    FORMAL_CANDIDATE_DOMAIN,
    SEARCH_SEMANTICS_BRIDGE_DOMAIN,
    REQUEST_DOMAIN,
    RESULT_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != 6
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover
    raise RuntimeError("H1 business-adapter domains are not uniquely registered")

_PROFILE_ISSUER = object()
_REQUEST_ISSUER = object()
_RESULT_ISSUER = object()
_LIVE_REQUESTS: dict[int, tuple[object, bytes]] = {}
_LIVE_RESULTS: dict[int, tuple[object, bytes]] = {}
_FROZEN_SEARCH_SEMANTICS_DERIVER = (
    route_v4.derive_owned_engine_search_semantics_v4
)

OWNED_PATHS = (
    "fallback.states_expanded",
    "fallback.actions_evaluated",
    "fallback.ground_steps",
    "fallback.outcome_rows",
    "fallback.bellman_backups",
    "control.cap_checks",
    "control.cap_rejections",
)
OBSERVED_FORBIDDEN_CALLS = (
    "kernel_step_calls",
    "ground_outcome_enumerations",
    "planner_calls",
    "j0_calls",
    "fallback_solver_calls",
    "postrun_artifact_reads",
)

_CURRENT_CANDIDATE_FIELDS = frozenset(
    {
        "schema",
        "current_access_candidate_id",
        "observed_access_log_id",
        "route_decision_freeze_barrier_id",
        "identity",
        "predecision_read_barrier_sequence",
        "route_decision_freeze_sequence",
        "observed_forbidden_call_counts",
        "route_time_ground_free",
        "production_current_access_authority",
        "construction_candidate",
        "production_consumers_must_reject_candidate",
    }
)
_FORMAL_CANDIDATE_FIELDS = frozenset(
    {
        "schema",
        "formal_v7_decision_candidate_id",
        "RouteDecisionContext_id",
        "decision_point_id",
        "formal_v7_route_upper_id",
        "formal_v7_route_decision_id",
        "selected_route",
        "structural_id",
        "query_id",
        "selected_plan_id",
        "threshold_profile_id",
        "BuildEpoch_id",
        "kernel_id",
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
        "exact_infeasibility_identity_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "ground_fallback_cap_profile_id",
        "ground_fallback_cardinality_bound_id",
        "cardinality_evidence_id",
        "route_upper_formula_id",
        "route_upper_derivation_proof_id",
        "counter_registry_id",
        "stage_profile_id",
        "comparison_profile_id",
        "actual_projection_profile_id",
        "decision_verification_sequence",
        "route_decision_freeze_sequence",
        "route_decision_freeze_barrier_id",
        "formal_v7_route_authority",
        "construction_candidate",
        "production_consumers_must_reject_candidate",
    }
)


class ConstructionK7H1BusinessAdapterV1Error(ValueError):
    """The H1 request/result chain is not exact."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1BusinessAdapterV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BusinessAdapterV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _exact_document(value: Any, fields: frozenset[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or frozenset(value) != fields:
        _fail(f"{label} fields are not exact")
    try:
        raw = canonical_json_bytes(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BusinessAdapterV1Error(
            f"{label} is outside canonical JSON"
        ) from error
    if not raw:
        _fail(f"{label} is empty")
    return dict(value)


def _canonical_h1_query(kernel: G2048Kernel) -> QuerySpec[Any]:
    return QuerySpec(
        kernel.initial_distribution(),
        1,
        (("merge", Fraction(1)),),
        "default",
        Fraction(1, 20),
        Fraction(1),
        "g2048.canonical.merge_le_1_per_step.total_le_h.v1",
    )


def _derive_canonical_h1_search_semantics() -> route_v4.OwnedEngineSearchSemanticsV4:
    if (
        route_v4.derive_owned_engine_search_semantics_v4
        is not _FROZEN_SEARCH_SEMANTICS_DERIVER
    ):
        _fail("owned search-semantics derivation entry changed")
    kernel = G2048Kernel(2)
    semantics = _FROZEN_SEARCH_SEMANTICS_DERIVER(
        kernel,
        _canonical_h1_query(kernel),
    )
    if type(semantics) is not route_v4.OwnedEngineSearchSemanticsV4:
        _fail("canonical H1 replay did not derive exact owned search semantics")
    return semantics


def _durable_query_rows(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"probability": row["probability"], "state": row["state"]}
        for row in document["query_profile"]["initial_distribution"]
    ]
    rows.sort(key=canonical_json_bytes)
    return rows


def _owned_query_rows(document: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in document["query"]["initial_distribution"]:
        state = row["state"]
        fields = state["fields"]
        rows.append(
            {
                "probability": row["probability"],
                "state": {
                    "board": fields["board"],
                    "status": fields["status"]["value"],
                },
            }
        )
    rows.sort(key=canonical_json_bytes)
    return rows


def _bridge_canonical_h1_search_semantics(
    *,
    durable_proof_bytes: bytes,
    current_identity: DurableExactInfeasibilityIdentityV1,
) -> tuple[route_v4.OwnedEngineSearchSemanticsV4, dict[str, Any]]:
    if type(durable_proof_bytes) is not bytes:
        _fail("durable proof replay requires immutable bytes")
    verified = verify_phase3e_exact_infeasibility_durable_proof_bytes_v1(
        durable_proof_bytes,
        current_identity=current_identity,
    )
    if (
        verified.result.outcome
        is not DurableProofVerificationOutcomeV1.IDENTICAL_MATCH
        or verified.proof_identity != current_identity
        or verified.result.durable_proof_id is None
    ):
        _fail("durable proof did not replay against the exact request identity")
    try:
        durable = loads_canonical_json(durable_proof_bytes)
        semantics = _derive_canonical_h1_search_semantics()
        owned = loads_canonical_json(semantics.semantic_documents_bytes)
        durable_structure = durable["structural_profile"]
        owned_structure = owned["structural"]
        durable_reward = durable["reward_profile"]
        owned_reward = owned["reward"]
        durable_policy = durable["policy_class_profile"]
        owned_policy = owned["policy_class"]
        durable_search = durable["complete_search_profile"]
        owned_search = owned["search_profile"]
        durable_spawn = [
            [row["rank"], row["probability"]]
            for row in durable_structure["spawn_rank_distribution"]
        ]
        owned_spawn = owned_structure["public_structure"]["spawn_distribution"]
        durable_rewards = [
            [row["feature"], row["coefficient"]]
            for row in durable_reward["reward_weights"]
        ]
        if (
            durable["identity"] != current_identity.to_dict()
            or owned_structure["kernel_config"]["fields"]["size"] != 2
            or owned_structure["public_structure"]["rank_cap"] != 6
            or durable_structure["board_geometry"] != "orthogonal_2x2"
            or durable_structure["rank_set"] != [1, 2, 3, 4, 5, 6]
            or durable_spawn != owned_spawn
            or _durable_query_rows(durable) != _owned_query_rows(owned)
            or durable["query_profile"]["horizon"]
            != owned["query"]["horizon"]
            or durable["query_profile"]["goal"] != owned["query"]["goal"]
            or durable["threshold_profile"]["delta"]
            != owned["threshold"]["delta"]
            or durable_rewards != owned_reward["reward_weights"]
            or durable_reward["normalizer"] != owned_reward["normalizer"]
            or durable_reward["normalizer_proof_id"]
            != owned_reward["normalizer_proof_id"]
            or durable_policy["policy_class"]
            != owned_policy["policy_class"]
            or durable_policy["randomized_ground_policy"] is not False
            or durable_policy["query_time_policy_mixture"] is not False
            or owned_policy["randomized_policy"] is not False
            or owned_policy["policy_mixture"] is not False
            or durable_search["search_complete"] is not True
            or durable_search["cap_exhausted"] is not False
            or durable["query_profile"]["horizon"] != 1
            or owned_search["horizon"] != 1
            or owned_search["exact_rational"] is not True
        ):
            _fail("durable H1 documents and derived V4 semantics differ")
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7H1BusinessAdapterV1Error(
            "durable/V4 search-semantics bridge is malformed"
        ) from error

    durable_components = {
        "structural_id": current_identity.structural_id,
        "kernel_id": current_identity.kernel_id,
        "query_id": current_identity.query_id,
        "threshold_profile_id": current_identity.threshold_profile_id,
        "reward_profile_id": current_identity.reward_profile_id,
        "policy_class_id": current_identity.policy_class_id,
        "complete_search_profile_id": current_identity.complete_search_profile_id,
        "exact_infeasibility_identity_id": (
            current_identity.exact_infeasibility_identity_id
        ),
    }
    owned_components = {
        "structural_id": semantics.structural_id,
        "kernel_id": semantics.kernel_id,
        "derived_query_id": semantics.derived_query_id,
        "threshold_profile_id": semantics.threshold_profile_id,
        "reward_profile_id": semantics.reward_profile_id,
        "policy_class_id": semantics.policy_class_id,
        "complete_search_profile_id": semantics.complete_search_profile_id,
    }
    durable_semantic_documents = {
        name: durable[name]
        for name in (
            "structural_profile",
            "kernel_profile",
            "query_profile",
            "threshold_profile",
            "reward_profile",
            "policy_class_profile",
            "complete_search_profile",
        )
    }
    bridge = {
        "schema": "acfqp.h1_search_semantics_bridge.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "durable_proof_id": verified.result.durable_proof_id,
        "durable_proof_sha256": hashlib.sha256(durable_proof_bytes).hexdigest(),
        "durable_proof_byte_count": len(durable_proof_bytes),
        "durable_components": durable_components,
        "durable_semantic_documents": durable_semantic_documents,
        "owned_search_semantics_id": semantics.semantics_id,
        "owned_components": owned_components,
        "owned_semantic_documents": owned,
        "kernel_replay_document_id": semantics.kernel_id,
        "query_replay_document_id": semantics.derived_query_id,
        "bridge_scope": "METADATA_CONFIGURATION_COMPATIBILITY_ONLY",
        "transition_table_equivalence_proved": False,
        "durable_kernel_source_equivalence_proved": False,
        "canonical_h1_semantics_derived_without_ground_step": True,
        "caller_semantic_label_accepted": False,
        "sealed_fresh_exec_replay_observed": False,
        "fresh_exec_transition_authority": False,
        "production_authority": False,
        "production_consumers_must_reject_candidate": True,
        "construction_only": True,
    }
    return semantics, {
        **bridge,
        "h1_search_semantics_bridge_id": content_id(
            SEARCH_SEMANTICS_BRIDGE_DOMAIN, bridge
        ),
    }


@runtime_checkable
class H1ProductionCurrentAccessCandidateV1(Protocol):
    """Nonauthoritative fixture surface for a future observed authority."""

    @property
    def current_access_candidate_id(self) -> str: ...

    @property
    def observed_access_log_id(self) -> str: ...

    @property
    def route_decision_freeze_barrier_id(self) -> str: ...

    @property
    def identity(self) -> DurableExactInfeasibilityIdentityV1: ...

    @property
    def predecision_read_barrier_sequence(self) -> int: ...

    @property
    def route_decision_freeze_sequence(self) -> int: ...

    def to_document(self) -> dict[str, Any]: ...


@runtime_checkable
class H1FormalV7FallbackDecisionCandidateV1(Protocol):
    """Nonauthoritative fixture surface for the future 182-term authority."""

    @property
    def formal_v7_decision_candidate_id(self) -> str: ...

    @property
    def decision_verification_sequence(self) -> int: ...

    @property
    def route_decision_freeze_sequence(self) -> int: ...

    @property
    def route_decision_freeze_barrier_id(self) -> str: ...

    def to_document(self) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class H1BusinessAdapterProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("H1 business-adapter profile is issuer-owned")
        object.__setattr__(self, "_profile_id", content_id(PROFILE_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_business_adapter_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "accepted_outcomes": [
                GroundFallbackOutcome.INFEASIBLE_CERTIFIED.value,
                GroundFallbackOutcome.CAP_EXHAUSTED.value,
            ],
            "feasible_result_supported_for_canonical_h1": False,
            "contract_2_0_52_current_candidate_accepted": False,
            "nonauthoritative_current_access_candidate_required": True,
            "nonauthoritative_formal_v7_decision_candidate_required": True,
            "production_request_factory_fail_closed": True,
            "production_result_factory_fail_closed": True,
            "reserved_class_exact_type_is_authority": False,
            "production_authority_require_functions_always_reject": True,
            "legacy_contract_2_0_50_upper_or_decision_accepted": False,
            "postrun_object_accepted_by_request": False,
            "owned_transcript_required": True,
            "durable_to_owned_search_semantics_bridge_required": True,
            "caller_search_semantic_label_accepted": False,
            "fresh_exec_search_semantics_authority_present": False,
            "legacy_search_work_vector_promoted": False,
            "formal_counter_records_issued": 0,
            "formal_work_vectors_issued": 0,
            "formal_comparison_vectors_issued": 0,
            "process_runtime_wired": False,
            "official_execution_allowed": False,
            "construction_only": True,
        }

    @property
    def profile_id(self) -> str:
        if content_id(PROFILE_DOMAIN, self._payload()) != self._profile_id:
            _fail("H1 business-adapter profile changed")
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_business_adapter_profile_id": self.profile_id}


_OFFICIAL_PROFILE = H1BusinessAdapterProfileV1(_PROFILE_ISSUER)


def official_h1_business_adapter_profile_v1() -> H1BusinessAdapterProfileV1:
    return _OFFICIAL_PROFILE


def _v6_profile_ids() -> dict[str, str]:
    registry = registry_v6.official_counter_registry_v6()
    stage = registry_v6.official_stage_profile_v6(registry)
    comparison = registry_v6.official_comparison_profile_v6(registry)
    projection = registry_v6.official_actual_projection_profile_v6(
        registry, comparison
    )
    return {
        "counter_registry_id": registry.registry_id,
        "stage_profile_id": stage.stage_profile_id,
        "comparison_profile_id": comparison.comparison_profile_id,
        "actual_projection_profile_id": projection.actual_projection_profile_id,
    }


class H1ProductionBusinessRequestV1:
    """Reserved surface; allocation never constitutes production authority."""

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "H1ProductionBusinessRequestV1":
        _fail("production current-access/formal V7 authorities are not implemented")


def require_h1_production_business_request_authority_v1(
    _value: Any,
) -> NoReturn:
    """Always reject: no valid request authority can currently be verified."""

    _fail(
        "no valid H1 production business-request authority can be issued or "
        "verified; exact class identity is never sufficient"
    )


@dataclass(frozen=True, slots=True)
class H1ProductionBusinessRequestCandidateV1:
    _issuer: InitVar[object]
    fields: Mapping[str, Any]
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REQUEST_ISSUER or type(self.fields) is not dict:
            _fail("H1 production business request is issuer-owned")
        object.__setattr__(self, "_request_id", content_id(REQUEST_DOMAIN, dict(self.fields)))

    def _payload(self) -> dict[str, Any]:
        return dict(self.fields)

    @property
    def request_id(self) -> str:
        raw = canonical_json_bytes(self.to_document_unchecked())
        retained = _LIVE_REQUESTS.get(id(self))
        if (
            content_id(REQUEST_DOMAIN, self._payload()) != self._request_id
            or retained is None
            or retained[0] is not self
            or not hmac.compare_digest(retained[1], raw)
        ):
            _fail("H1 production business request changed or lost retention")
        return self._request_id

    def to_document_unchecked(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_production_business_request_candidate_id": self._request_id,
        }

    def to_document(self) -> dict[str, Any]:
        _ = self.request_id
        return self.to_document_unchecked()

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    @property
    def byte_count(self) -> int:
        return len(self.canonical_bytes)


def replay_h1_request_search_semantics_v1(
    request: H1ProductionBusinessRequestCandidateV1,
) -> route_v4.OwnedEngineSearchSemanticsV4:
    """Re-derive, rather than trust, the canonical H1 V4 search semantics."""

    if type(request) is not H1ProductionBusinessRequestCandidateV1:
        _fail("search-semantics replay requires one exact retained H1 request")
    document = request.to_document()
    semantics = _derive_canonical_h1_search_semantics()
    expected_components = {
        "search_semantics_id": semantics.semantics_id,
        "search_semantics_structural_id": semantics.structural_id,
        "search_semantics_kernel_id": semantics.kernel_id,
        "search_semantics_derived_query_id": semantics.derived_query_id,
        "search_semantics_threshold_profile_id": semantics.threshold_profile_id,
        "search_semantics_reward_profile_id": semantics.reward_profile_id,
        "search_semantics_policy_class_id": semantics.policy_class_id,
        "search_semantics_complete_search_profile_id": (
            semantics.complete_search_profile_id
        ),
        "kernel_replay_document_id": semantics.kernel_id,
        "query_replay_document_id": semantics.derived_query_id,
    }
    bridge = document.get("search_semantics_bridge")
    if (
        document.get("search_semantics") != semantics.to_document()
        or any(document.get(name) != value for name, value in expected_components.items())
        or type(bridge) is not dict
        or bridge.get("h1_search_semantics_bridge_id")
        != document.get("h1_search_semantics_bridge_id")
    ):
        _fail("retained H1 request search semantics differ from canonical replay")
    bridge_payload = dict(bridge)
    bridge_id = bridge_payload.pop("h1_search_semantics_bridge_id")
    if (
        content_id(SEARCH_SEMANTICS_BRIDGE_DOMAIN, bridge_payload) != bridge_id
        or bridge_payload.get("owned_search_semantics_id") != semantics.semantics_id
        or bridge_payload.get("owned_components")
        != {
            "structural_id": semantics.structural_id,
            "kernel_id": semantics.kernel_id,
            "derived_query_id": semantics.derived_query_id,
            "threshold_profile_id": semantics.threshold_profile_id,
            "reward_profile_id": semantics.reward_profile_id,
            "policy_class_id": semantics.policy_class_id,
            "complete_search_profile_id": semantics.complete_search_profile_id,
        }
        or bridge_payload.get("owned_semantic_documents")
        != loads_canonical_json(semantics.semantic_documents_bytes)
        or bridge_payload.get("bridge_scope")
        != "METADATA_CONFIGURATION_COMPATIBILITY_ONLY"
        or bridge_payload.get("transition_table_equivalence_proved") is not False
        or bridge_payload.get("durable_kernel_source_equivalence_proved") is not False
        or bridge_payload.get("caller_semantic_label_accepted") is not False
        or bridge_payload.get("sealed_fresh_exec_replay_observed") is not False
        or bridge_payload.get("fresh_exec_transition_authority") is not False
        or bridge_payload.get("production_authority") is not False
        or bridge_payload.get("production_consumers_must_reject_candidate")
        is not True
    ):
        _fail("retained H1 durable/V4 semantics bridge changed")
    return semantics


def freeze_h1_production_business_request_candidate_v1(
    *,
    recipe: recipe_v1.H1DirectFallbackTwoRoleRecipeV1,
    preexecution_candidate_bytes: bytes,
    current_access_candidate: H1ProductionCurrentAccessCandidateV1,
    formal_route_candidate: H1FormalV7FallbackDecisionCandidateV1,
    durable_proof_bytes: bytes,
    owned_engine_source_bytes: bytes,
    owned_engine_authority: route_v4.VerifiedOwnedEngineAuthorityV4,
    route_segment_id: str,
    recorder_id: str,
    issuance_sequence: int,
) -> H1ProductionBusinessRequestCandidateV1:
    """Freeze a nonauthoritative post-decision request construction fixture."""

    if type(recipe) is not recipe_v1.H1DirectFallbackTwoRoleRecipeV1:
        _fail("H1 request requires the exact retained two-role recipe")
    _ = recipe.recipe_id
    if (
        type(preexecution_candidate_bytes) is not bytes
        or hashlib.sha256(preexecution_candidate_bytes).hexdigest()
        != recipe.source.preexecution_sha256
    ):
        _fail("H1 request preexecution bytes differ from its exact recipe")
    replayed_recipe = recipe_v1.verify_h1_direct_fallback_two_role_recipe_bytes_v1(
        raw=recipe.canonical_bytes,
        preexecution_candidate_bytes=preexecution_candidate_bytes,
    )
    if replayed_recipe.to_document() != recipe.to_document():
        _fail("H1 request recipe did not replay exactly")

    if type(current_access_candidate) is current_v1.H1ProductionCurrentIdentityCandidateV1:
        _fail("Contract 2.0.52 current candidate is never a production authority")
    if not isinstance(current_access_candidate, H1ProductionCurrentAccessCandidateV1):
        _fail("current-access candidate interface is unsatisfied")
    current = _exact_document(
        current_access_candidate.to_document(),
        _CURRENT_CANDIDATE_FIELDS,
        "current-access candidate",
    )
    if (
        current.get("schema") != "acfqp.h1_current_access_candidate.v1"
        or current.get("production_current_access_authority") is not False
        or current.get("construction_candidate") is not True
        or current.get("production_consumers_must_reject_candidate") is not True
        or current.get("route_time_ground_free") is not True
        or current.get("current_access_candidate_id")
        != current_access_candidate.current_access_candidate_id
        or current.get("observed_access_log_id")
        != current_access_candidate.observed_access_log_id
        or current.get("route_decision_freeze_barrier_id")
        != current_access_candidate.route_decision_freeze_barrier_id
        or current.get("predecision_read_barrier_sequence")
        != current_access_candidate.predecision_read_barrier_sequence
        or current.get("route_decision_freeze_sequence")
        != current_access_candidate.route_decision_freeze_sequence
        or current.get("observed_forbidden_call_counts")
        != {name: 0 for name in OBSERVED_FORBIDDEN_CALLS}
    ):
        _fail("current-access candidate lacks exact nonauthority zero-ground evidence")
    for name in (
        "current_access_candidate_id",
        "observed_access_log_id",
        "route_decision_freeze_barrier_id",
    ):
        _cid(current[name], name)
    current_payload = dict(current)
    current_identifier = current_payload.pop("current_access_candidate_id")
    if content_id(CURRENT_CANDIDATE_DOMAIN, current_payload) != current_identifier:
        _fail("current-access candidate content identity is invalid")
    try:
        current_identity = DurableExactInfeasibilityIdentityV1.from_dict(current["identity"])
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1BusinessAdapterV1Error(
            "production current-access identity is invalid"
        ) from error
    if current_identity != current_access_candidate.identity:
        _fail("current-access candidate protocol and document identities differ")

    if not isinstance(formal_route_candidate, H1FormalV7FallbackDecisionCandidateV1):
        _fail("formal V7 decision candidate interface is unsatisfied")
    formal = _exact_document(
        formal_route_candidate.to_document(),
        _FORMAL_CANDIDATE_FIELDS,
        "formal V7 decision candidate",
    )
    if (
        formal.get("schema") != "acfqp.h1_formal_v7_decision_candidate.v1"
        or formal.get("formal_v7_route_authority") is not False
        or formal.get("construction_candidate") is not True
        or formal.get("production_consumers_must_reject_candidate") is not True
        or formal.get("selected_route") != "FALLBACK"
        or formal.get("formal_v7_decision_candidate_id")
        != formal_route_candidate.formal_v7_decision_candidate_id
        or formal.get("decision_verification_sequence")
        != formal_route_candidate.decision_verification_sequence
        or formal.get("route_decision_freeze_sequence")
        != formal_route_candidate.route_decision_freeze_sequence
        or formal.get("route_decision_freeze_barrier_id")
        != formal_route_candidate.route_decision_freeze_barrier_id
    ):
        _fail("formal V7 candidate is malformed or did not select FALLBACK")
    for name in _FORMAL_CANDIDATE_FIELDS - {
        "schema",
        "selected_route",
        "decision_verification_sequence",
        "route_decision_freeze_sequence",
        "formal_v7_route_authority",
        "construction_candidate",
        "production_consumers_must_reject_candidate",
    }:
        _cid(formal[name], name)
    formal_payload = dict(formal)
    formal_identifier = formal_payload.pop("formal_v7_decision_candidate_id")
    if content_id(FORMAL_CANDIDATE_DOMAIN, formal_payload) != formal_identifier:
        _fail("formal V7 decision candidate content identity is invalid")
    if (
        formal["formal_v7_route_upper_id"] == recipe.source.legacy_selected_upper_id
        or formal["formal_v7_route_decision_id"] == recipe.source.legacy_route_decision_id
    ):
        _fail("Contract 2.0.50 upper/decision cannot authorize H1 production")
    expected_chain = {
        "structural_id": recipe.source.structural_id,
        "query_id": recipe.source.query_id,
        "selected_plan_id": recipe.source.selected_plan_id,
        "threshold_profile_id": recipe.source.threshold_profile_id,
        "BuildEpoch_id": recipe.source.build_epoch_id,
        "kernel_id": recipe.source.kernel_id,
        "reward_profile_id": current_identity.reward_profile_id,
        "policy_class_id": current_identity.policy_class_id,
        "complete_search_profile_id": current_identity.complete_search_profile_id,
        "exact_infeasibility_identity_id": (
            current_identity.exact_infeasibility_identity_id
        ),
        "logical_occurrence_id": recipe.source.logical_occurrence_id,
        "route_attempt_id": recipe.source.route_attempt_id,
    }
    if any(formal[name] != value for name, value in expected_chain.items()):
        _fail("formal V7 decision crossed the frozen H1 recipe identity")
    if (
        recipe.source.exact_infeasibility_identity_id
        != current_identity.exact_infeasibility_identity_id
        or
        current_identity.structural_id != formal["structural_id"]
        or current_identity.query_id != formal["query_id"]
        or current_identity.threshold_profile_id != formal["threshold_profile_id"]
        or current_identity.build_epoch_id != formal["BuildEpoch_id"]
        or current_identity.kernel_id != formal["kernel_id"]
        or current_identity.reward_profile_id != formal["reward_profile_id"]
        or current_identity.policy_class_id != formal["policy_class_id"]
        or current_identity.complete_search_profile_id
        != formal["complete_search_profile_id"]
        or current_identity.exact_infeasibility_identity_id
        != formal["exact_infeasibility_identity_id"]
    ):
        _fail("current, formal and recipe identities crossed")
    v6 = _v6_profile_ids()
    if any(formal[name] != value for name, value in v6.items()):
        _fail("formal V7 decision does not bind the exact V6 profiles")
    if (
        type(current_access_candidate.predecision_read_barrier_sequence) is not int
        or current_access_candidate.predecision_read_barrier_sequence < 0
        or type(formal_route_candidate.decision_verification_sequence) is not int
        or type(formal_route_candidate.route_decision_freeze_sequence) is not int
        or current_access_candidate.route_decision_freeze_sequence
        != formal_route_candidate.route_decision_freeze_sequence
        or current_access_candidate.route_decision_freeze_barrier_id
        != formal_route_candidate.route_decision_freeze_barrier_id
        or not (
            current_access_candidate.predecision_read_barrier_sequence
            < formal_route_candidate.decision_verification_sequence
            < formal_route_candidate.route_decision_freeze_sequence
        )
        or type(issuance_sequence) is not int
        or issuance_sequence <= formal_route_candidate.route_decision_freeze_sequence
    ):
        _fail("request issuance sequence or shared route freeze is invalid")

    search_semantics, search_bridge = _bridge_canonical_h1_search_semantics(
        durable_proof_bytes=durable_proof_bytes,
        current_identity=current_identity,
    )
    if search_bridge["durable_proof_id"] != recipe.source.durable_proof_id:
        _fail("durable semantics bridge crossed the frozen H1 recipe proof")

    if type(owned_engine_authority) is not route_v4.VerifiedOwnedEngineAuthorityV4:
        _fail("H1 request owned-engine authority is foreign")
    replayed_engine = route_v4.verify_sealed_owned_engine_authority_v4(
        owned_engine_source_bytes
    )
    if replayed_engine.to_document() != owned_engine_authority.to_document():
        _fail("H1 request owned-engine source and authority differ")
    if owned_engine_authority.counter_registry_id != v6["counter_registry_id"]:
        _fail("owned-engine authority does not bind the exact V6 registry")

    for value, label in ((route_segment_id, "route segment"),):
        _cid(value, label)
    if type(recorder_id) is not str or not recorder_id:
        _fail("H1 request recorder ID must be nonempty")
    search_registry = owned_v3.official_counter_registry_v1()
    payload = {
        "schema": "acfqp.h1_production_business_request_candidate.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_business_adapter_profile_id": _OFFICIAL_PROFILE.profile_id,
        "h1_direct_fallback_two_role_recipe_id": recipe.recipe_id,
        "legacy_h1_preexecution_candidate_id": recipe.source.preexecution_candidate_id,
        "legacy_h1_preexecution_candidate_sha256": recipe.source.preexecution_sha256,
        "legacy_h1_preexecution_candidate_byte_count": len(preexecution_candidate_bytes),
        "current_access_candidate_id": current["current_access_candidate_id"],
        "observed_access_log_id": current["observed_access_log_id"],
        "route_decision_freeze_barrier_id": current["route_decision_freeze_barrier_id"],
        "formal_v7_decision_candidate_id": formal["formal_v7_decision_candidate_id"],
        "RouteDecisionContext_id": formal["RouteDecisionContext_id"],
        "decision_point_id": formal["decision_point_id"],
        "formal_v7_route_upper_id": formal["formal_v7_route_upper_id"],
        "formal_v7_route_decision_id": formal["formal_v7_route_decision_id"],
        "selected_route": "FALLBACK",
        **expected_chain,
        "ground_fallback_cap_profile_id": formal["ground_fallback_cap_profile_id"],
        "ground_fallback_cardinality_bound_id": formal["ground_fallback_cardinality_bound_id"],
        "cardinality_evidence_id": formal["cardinality_evidence_id"],
        "route_upper_formula_id": formal["route_upper_formula_id"],
        "route_upper_derivation_proof_id": formal["route_upper_derivation_proof_id"],
        **v6,
        "owned_engine_source_sha256": owned_engine_authority.source_sha256,
        "owned_engine_source_byte_count": owned_engine_authority.source_byte_count,
        "owned_engine_authority_id": owned_engine_authority.authority_id,
        "owned_engine_stage_profile_id": owned_engine_authority.stage_profile_id,
        "owned_search_counter_registry_id": search_registry.registry_id,
        "route_segment_id": route_segment_id,
        "recorder_id": recorder_id,
        "durable_proof_id": search_bridge["durable_proof_id"],
        "durable_proof_sha256": search_bridge["durable_proof_sha256"],
        "durable_proof_byte_count": search_bridge["durable_proof_byte_count"],
        "h1_search_semantics_bridge_id": search_bridge[
            "h1_search_semantics_bridge_id"
        ],
        "search_semantics_bridge": search_bridge,
        "search_semantics": search_semantics.to_document(),
        "search_semantics_id": search_semantics.semantics_id,
        "search_semantics_structural_id": search_semantics.structural_id,
        "search_semantics_kernel_id": search_semantics.kernel_id,
        "search_semantics_derived_query_id": search_semantics.derived_query_id,
        "search_semantics_threshold_profile_id": (
            search_semantics.threshold_profile_id
        ),
        "search_semantics_reward_profile_id": search_semantics.reward_profile_id,
        "search_semantics_policy_class_id": search_semantics.policy_class_id,
        "search_semantics_complete_search_profile_id": (
            search_semantics.complete_search_profile_id
        ),
        "kernel_replay_document_id": search_semantics.kernel_id,
        "query_replay_document_id": search_semantics.derived_query_id,
        "predecision_read_barrier_sequence": (
            current_access_candidate.predecision_read_barrier_sequence
        ),
        "decision_verification_sequence": (
            formal_route_candidate.decision_verification_sequence
        ),
        "route_decision_freeze_sequence": (
            formal_route_candidate.route_decision_freeze_sequence
        ),
        "request_issuance_sequence": issuance_sequence,
        "observed_forbidden_call_counts": {name: 0 for name in OBSERVED_FORBIDDEN_CALLS},
        "post_formal_decision_issuance": True,
        "request_api_accepts_kernel_or_query_objects": False,
        "request_api_accepts_postrun_counter_result_or_work_vector": False,
        "legacy_upper_or_decision_used_as_authority": False,
        "production_request_authority": False,
        "current_access_authority_present": False,
        "formal_v7_route_authority_present": False,
        "candidate_domains_are_role_separated": True,
        "production_consumers_must_reject_candidate": True,
        "production_execution_authorized": False,
        "formal_counter_records_issued": 0,
        "formal_work_vectors_issued": 0,
        "formal_comparison_vectors_issued": 0,
        "official_execution_allowed": False,
        "construction_only": True,
    }
    request = H1ProductionBusinessRequestCandidateV1(_REQUEST_ISSUER, payload)
    raw = canonical_json_bytes(request.to_document_unchecked())
    _LIVE_REQUESTS[id(request)] = (request, raw)
    return request


def freeze_h1_production_business_request_v1(
    **_kwargs: Any,
) -> H1ProductionBusinessRequestV1:
    """Fail closed until concrete current-access and formal V7 authorities exist."""

    _fail(
        "production H1 request issuance is blocked: current-access and formal V7 "
        "authority classes are not implemented"
    )


class H1ProductionBusinessResultV1:
    """Reserved surface; allocation never constitutes production authority."""

    def __new__(cls, *_args: Any, **_kwargs: Any) -> "H1ProductionBusinessResultV1":
        _fail("production H1 request/runtime authority is not implemented")


def require_h1_production_business_result_authority_v1(
    _value: Any,
) -> NoReturn:
    """Always reject: no valid result authority can currently be verified."""

    _fail(
        "no valid H1 production business-result authority can be issued or "
        "verified; exact class identity is never sufficient"
    )


@dataclass(frozen=True, slots=True)
class H1ProductionBusinessResultCandidateV1:
    _issuer: InitVar[object]
    fields: Mapping[str, Any]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RESULT_ISSUER or type(self.fields) is not dict:
            _fail("H1 production business result is issuer-owned")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, dict(self.fields)))

    def _payload(self) -> dict[str, Any]:
        return dict(self.fields)

    @property
    def result_id(self) -> str:
        raw = canonical_json_bytes(self.to_document_unchecked())
        retained = _LIVE_RESULTS.get(id(self))
        if (
            content_id(RESULT_DOMAIN, self._payload()) != self._result_id
            or retained is None
            or retained[0] is not self
            or not hmac.compare_digest(retained[1], raw)
        ):
            _fail("H1 production business result changed or lost retention")
        return self._result_id

    def to_document_unchecked(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_production_business_result_candidate_id": self._result_id,
        }

    def to_document(self) -> dict[str, Any]:
        _ = self.result_id
        return self.to_document_unchecked()

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes).hexdigest()

    @property
    def byte_count(self) -> int:
        return len(self.canonical_bytes)


def issue_h1_production_business_result_candidate_v1(
    *,
    request: H1ProductionBusinessRequestCandidateV1,
    execution: GroundFallbackExecutionV1,
    owned_transcript: route_v4.OwnedEngineRouteSegmentTranscriptV4,
) -> H1ProductionBusinessResultCandidateV1:
    """Bind an exact owned transcript to a nonauthoritative result fixture."""

    if type(request) is not H1ProductionBusinessRequestCandidateV1:
        _fail("H1 result requires its exact retained request")
    request_doc = request.to_document()
    if type(execution) is not GroundFallbackExecutionV1:
        _fail("H1 result execution has the wrong type")
    if type(owned_transcript) is not route_v4.OwnedEngineRouteSegmentTranscriptV4:
        _fail("H1 result requires one exact owned-engine transcript")
    transcript_doc = owned_transcript.to_document()
    start = owned_transcript.start
    terminal = owned_transcript.terminal
    if (
        terminal.terminal_kind is not route_v4.RouteSegmentTerminalKindV4.COMPLETED
        or terminal.exact_search_finished is not True
        or start.route_segment_id != request_doc["route_segment_id"]
        or start.occurrence_id != request_doc["logical_occurrence_id"]
        or start.route_attempt_id != request_doc["route_attempt_id"]
        or start.recorder_id != request_doc["recorder_id"]
        or start.owned_engine_authority_id != request_doc["owned_engine_authority_id"]
        or start.counter_registry_id != request_doc["counter_registry_id"]
        or start.stage_profile_id != request_doc["owned_engine_stage_profile_id"]
        or start.route_decision_context_id != request_doc["RouteDecisionContext_id"]
        or start.decision_point_id != request_doc["decision_point_id"]
        or start.route_decision_id != request_doc["formal_v7_route_decision_id"]
        or start.selected_upper_id != request_doc["formal_v7_route_upper_id"]
        or start.query_id != request_doc["query_id"]
        or start.ground_fallback_cap_profile_id
        != request_doc["ground_fallback_cap_profile_id"]
        or start.search_counter_registry_id
        != request_doc["owned_search_counter_registry_id"]
    ):
        _fail("H1 owned transcript start crossed its exact request")
    request_search_semantics = replay_h1_request_search_semantics_v1(request)
    start_search_semantics = start.search_semantics
    if (
        type(start_search_semantics) is not route_v4.OwnedEngineSearchSemanticsV4
        or start_search_semantics.to_document()
        != request_search_semantics.to_document()
        or (
            start_search_semantics.semantics_id,
            start_search_semantics.structural_id,
            start_search_semantics.kernel_id,
            start_search_semantics.derived_query_id,
            start_search_semantics.threshold_profile_id,
            start_search_semantics.reward_profile_id,
            start_search_semantics.policy_class_id,
            start_search_semantics.complete_search_profile_id,
        )
        != (
            request_doc["search_semantics_id"],
            request_doc["search_semantics_structural_id"],
            request_doc["search_semantics_kernel_id"],
            request_doc["search_semantics_derived_query_id"],
            request_doc["search_semantics_threshold_profile_id"],
            request_doc["search_semantics_reward_profile_id"],
            request_doc["search_semantics_policy_class_id"],
            request_doc["search_semantics_complete_search_profile_id"],
        )
    ):
        _fail("H1 owned transcript search semantics crossed its exact request")
    finished_binding = terminal.finished_execution_binding
    if (
        type(finished_binding)
        is not route_v4.OwnedEngineFinishedExecutionBindingV4
        or finished_binding.route_segment_start_id != start.start_id
    ):
        _fail("H1 owned transcript lacks its exact finished-execution binding")
    try:
        verified_finished_binding = (
            route_v4.verify_owned_engine_finished_execution_binding_v4(
                finished_binding, execution
            )
        )
    except route_v4.ConstructionAccountingRouteSegmentV4Error as error:
        raise ConstructionK7H1BusinessAdapterV1Error(
            "H1 execution differs from the transcript-frozen fingerprint"
        ) from error
    if verified_finished_binding is not finished_binding:
        _fail("finished-execution verifier replaced its exact binding")
    result = execution.result
    work = execution.work_vector
    if any(
        actual != request_doc[key]
        for actual, key in (
            (result.route_decision_context_id, "RouteDecisionContext_id"),
            (result.decision_point_id, "decision_point_id"),
            (result.route_decision_id, "formal_v7_route_decision_id"),
            (result.selected_upper_id, "formal_v7_route_upper_id"),
            (result.route_attempt_id, "route_attempt_id"),
            (result.query_id, "query_id"),
            (result.ground_fallback_cap_profile_id, "ground_fallback_cap_profile_id"),
        )
    ):
        _fail("H1 search result crossed its exact request")
    if (
        result.work_vector_id != work.work_vector_id
        or work.counter_registry_id != request_doc["owned_search_counter_registry_id"]
        or work.subject_id != request_doc["route_attempt_id"]
    ):
        _fail("H1 legacy search WorkVector differs from its owned result")
    values = {path: owned_transcript.values.get(path, 0) for path in OWNED_PATHS}
    if (
        any(type(value) is not int or value < 0 for value in values.values())
        or sum(values.values()) != len(owned_transcript.events)
        or any(work.values.get(path) != value for path, value in values.items())
    ):
        _fail("H1 owned transcript, event count and legacy search values differ")

    frontier = [point.to_dict() for point in result.frontier]
    selected = {
        "policy_signature": [list(row) for row in result.selected_policy_signature],
        "expected_reward": result.selected_expected_reward,
        "failure_probability": result.selected_failure_probability,
    }
    if result.outcome is GroundFallbackOutcome.INFEASIBLE_CERTIFIED:
        # Policy text is implementation-canonical but not a scientific input;
        # exact H1 values and the single frontier point are normative.
        if (
            not result.search_complete
            or len(frontier) != 1
            or frontier[0]["expected_reward"] != Fraction(83, 2624)
            or frontier[0]["failure_probability"] != Fraction(383, 410)
            or result.selected_policy_signature
            or result.selected_expected_reward is not None
            or result.selected_failure_probability is not None
            or result.cap_exhausted_name is not None
            or result.composed_candidate_count != 16
            or values != {
                "fallback.states_expanded": 8,
                "fallback.actions_evaluated": 16,
                "fallback.ground_steps": 16,
                "fallback.outcome_rows": 96,
                "fallback.bellman_backups": 16,
                "control.cap_checks": 56,
                "control.cap_rejections": 0,
            }
            or len(owned_transcript.events) != 208
        ):
            _fail("completed canonical H1 infeasibility regression changed")
        selected = {"kind": "NOT_APPLICABLE", "reason": "INFEASIBLE_CERTIFIED"}
        cap = {"kind": "NOT_APPLICABLE", "reason": "SEARCH_COMPLETE"}
    elif result.outcome is GroundFallbackOutcome.CAP_EXHAUSTED:
        allowed_caps = {
            "max_cap_checks",
            "max_states_expanded",
            "max_actions_evaluated",
            "max_ground_steps",
            "max_outcome_rows",
            "max_composed_candidates",
            "max_bellman_backups",
        }
        if (
            result.search_complete
            or frontier
            or result.selected_policy_signature
            or result.selected_expected_reward is not None
            or result.selected_failure_probability is not None
            or result.cap_exhausted_name not in allowed_caps
            or values["control.cap_rejections"] != 1
        ):
            _fail("H1 cap exhaustion is not one exact completed owned prefix")
        selected = {"kind": "NOT_APPLICABLE", "reason": "CAP_EXHAUSTED"}
        cap = {"kind": "EXHAUSTED_CAP", "name": result.cap_exhausted_name}
    else:
        _fail("canonical H1 business adapter cannot emit a feasible result")

    payload = {
        "schema": "acfqp.h1_production_business_result_candidate.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_business_adapter_profile_id": _OFFICIAL_PROFILE.profile_id,
        "h1_production_business_request_candidate_id": request.request_id,
        "RouteDecisionContext_id": request_doc["RouteDecisionContext_id"],
        "decision_point_id": request_doc["decision_point_id"],
        "formal_v7_route_upper_id": request_doc["formal_v7_route_upper_id"],
        "formal_v7_route_decision_id": request_doc["formal_v7_route_decision_id"],
        "query_id": request_doc["query_id"],
        "route_attempt_id": request_doc["route_attempt_id"],
        "ground_fallback_cap_profile_id": request_doc["ground_fallback_cap_profile_id"],
        "owned_engine_authority_id": request_doc["owned_engine_authority_id"],
        "owned_engine_route_segment_start_id": start.start_id,
        "owned_engine_route_segment_transcript_id": owned_transcript.transcript_id,
        "owned_engine_finished_execution_binding_id": finished_binding.binding_id,
        "h1_search_semantics_bridge_id": request_doc[
            "h1_search_semantics_bridge_id"
        ],
        "search_semantics_id": request_doc["search_semantics_id"],
        "search_semantics_structural_id": request_doc[
            "search_semantics_structural_id"
        ],
        "search_semantics_kernel_id": request_doc["search_semantics_kernel_id"],
        "search_semantics_derived_query_id": request_doc[
            "search_semantics_derived_query_id"
        ],
        "search_semantics_threshold_profile_id": request_doc[
            "search_semantics_threshold_profile_id"
        ],
        "search_semantics_reward_profile_id": request_doc[
            "search_semantics_reward_profile_id"
        ],
        "search_semantics_policy_class_id": request_doc[
            "search_semantics_policy_class_id"
        ],
        "search_semantics_complete_search_profile_id": request_doc[
            "search_semantics_complete_search_profile_id"
        ],
        "owned_engine_route_segment_transcript_sha256": hashlib.sha256(canonical_json_bytes(transcript_doc)).hexdigest(),
        "owned_engine_route_segment_transcript_byte_count": len(canonical_json_bytes(transcript_doc)),
        "outcome": result.outcome.value,
        "search_complete": result.search_complete,
        "frontier": frontier,
        "selected": selected,
        "cap_outcome": cap,
        "composed_candidate_count": result.composed_candidate_count,
        "owned_event_count": len(owned_transcript.events),
        "owned_values": values,
        "legacy_search_result_id": result.ground_fallback_result_id,
        "legacy_search_work_vector": {
            "work_vector_id": work.work_vector_id,
            "role": "DIAGNOSTIC_SEARCH_HELPER_OUTPUT_ONLY",
            "formal_accounting_authority": False,
            "promoted_to_h1_work_vector": False,
        },
        "counter_record_set_id": None,
        "formal_work_vector_id": None,
        "comparison_vector_id": None,
        "semantic_authority": False,
        "authorizes_terminal_classification": False,
        "formal_accounting_authority": False,
        "production_runtime_attested": False,
        "production_result_authority": False,
        "production_consumers_must_reject_candidate": True,
        "official_execution_allowed": False,
        "construction_only": True,
    }
    issued = H1ProductionBusinessResultCandidateV1(_RESULT_ISSUER, payload)
    raw = canonical_json_bytes(issued.to_document_unchecked())
    _LIVE_RESULTS[id(issued)] = (issued, raw)
    return issued


def issue_h1_production_business_result_v1(
    **_kwargs: Any,
) -> H1ProductionBusinessResultV1:
    """Fail closed until a real production request and process runtime exist."""

    _fail(
        "production H1 result issuance is blocked: production request/runtime "
        "authority is not implemented"
    )


__all__ = (
    "CONSTRUCTION_ONLY",
    "COUNTER_COMPLETENESS_GATE_STATUS",
    "ConstructionK7H1BusinessAdapterV1Error",
    "FORMAL_V7_ROUTE_AUTHORITY_PRESENT",
    "H1BusinessAdapterProfileV1",
    "H1FormalV7FallbackDecisionCandidateV1",
    "H1ProductionBusinessRequestV1",
    "H1ProductionBusinessRequestCandidateV1",
    "H1ProductionBusinessResultV1",
    "H1ProductionBusinessResultCandidateV1",
    "H1ProductionCurrentAccessCandidateV1",
    "OBSERVED_FORBIDDEN_CALLS",
    "OFFICIAL_EXECUTION_ALLOWED",
    "OFFICIAL_N_BREAK_EVEN",
    "OFFICIAL_SCALAR_COST",
    "OWNED_PATHS",
    "PROCESS_RUNTIME_WIRED",
    "PRODUCTION_CURRENT_ACCESS_AUTHORITY_PRESENT",
    "PRODUCTION_REQUEST_SCHEMA_PRESENT",
    "PRODUCTION_REQUEST_AUTHORITY_PRESENT",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SAMPLE_EFFICIENCY_GATE_STATUS",
    "WORKLOAD_ECONOMICS_GATE_STATUS",
    "freeze_h1_production_business_request_v1",
    "freeze_h1_production_business_request_candidate_v1",
    "issue_h1_production_business_result_v1",
    "issue_h1_production_business_result_candidate_v1",
    "official_h1_business_adapter_profile_v1",
    "replay_h1_request_search_semantics_v1",
    "require_h1_production_business_request_authority_v1",
    "require_h1_production_business_result_authority_v1",
)
