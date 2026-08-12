"""Route fresh H=2 queries through the verified structural model catalogue.

An exact structural hit reconstructs only the selected immutable interval
model and runs the quotient planner once.  A miss emits a typed construction
request without opening an observer, authorizing ground work, or silently
transferring a nearby model.  This is the consumer boundary between reusable
world-model storage and the later certificate-gated construction pipeline.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_heldout_reusable_model_catalogue_v1 as catalogue_v1
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_CONSTRUCTION_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.137"
PROFILE_KEY = "construction_k7_heldout_catalogue_query_router_v1"

QUERY_DOMAIN = CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_V1_DOMAIN
REQUEST_DOMAIN = CONSTRUCTION_K7_HELDOUT_CATALOGUE_CONSTRUCTION_REQUEST_V1_DOMAIN
PLAN_DOMAIN = CONSTRUCTION_K7_HELDOUT_CATALOGUE_ABSTRACT_PLAN_V1_DOMAIN
RESULT_DOMAIN = CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset({QUERY_DOMAIN, REQUEST_DOMAIN, PLAN_DOMAIN, RESULT_DOMAIN})
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("held-out catalogue-query domains are not central")

_QUERY_ISSUER = object()
_REQUEST_ISSUER = object()
_PLAN_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7HeldoutCatalogueQueryRouterV1Error(ValueError):
    """The catalogue selection, source model, or routed result changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutCatalogueQueryRouterV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCatalogueQueryRouterV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class HeldoutCatalogueQueryV1:
    _issuer: InitVar[object]
    catalogue_id: str
    selection_id: str
    logical_occurrence_id: str
    occurrence_ordinal: int
    context_key: str
    context_id: str
    topology_id: str
    selection_outcome: str
    selected_entry_id: str | None
    _query_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _QUERY_ISSUER:
            _fail("catalogue query is caller-minted")
        for value, label in (
            (self.catalogue_id, "query catalogue"),
            (self.selection_id, "query selection"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.context_id, "query context"),
            (self.topology_id, "query topology"),
        ):
            _cid(value, label)
        if (
            type(self.context_key) is not str
            or not self.context_key
            or type(self.occurrence_ordinal) is not int
            or self.occurrence_ordinal <= 0
            or self.selection_outcome not in {"EXACT_MODEL_MATCH", "MODEL_MISS"}
            or (
                (self.selection_outcome == "EXACT_MODEL_MATCH")
                != (self.selected_entry_id is not None)
            )
        ):
            _fail("catalogue query shape changed")
        if self.selected_entry_id is not None:
            _cid(self.selected_entry_id, "query selected entry")
        object.__setattr__(self, "_query_id", content_id(QUERY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_query.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "model_catalogue_id": self.catalogue_id,
            "model_selection_id": self.selection_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "occurrence_ordinal": self.occurrence_ordinal,
            "context_key": self.context_key,
            "context_id": self.context_id,
            "topology_id": self.topology_id,
            "horizon": 2,
            "selection_outcome": self.selection_outcome,
            "selected_model_catalogue_entry_id": self.selected_entry_id,
            "query_frozen_before_model_replay_or_planning": True,
            "observer_or_ground_input_present": False,
        }

    @property
    def query_id(self) -> str:
        current = content_id(QUERY_DOMAIN, self._payload())
        if current != self._query_id:
            _fail("catalogue query changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_query_id": self.query_id}


@dataclass(frozen=True, slots=True)
class HeldoutCatalogueConstructionRequestV1:
    _issuer: InitVar[object]
    query: HeldoutCatalogueQueryV1
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _REQUEST_ISSUER
            or type(self.query) is not HeldoutCatalogueQueryV1
            or self.query.selection_outcome != "MODEL_MISS"
            or self.query.selected_entry_id is not None
        ):
            _fail("construction request is not an exact catalogue miss")
        object.__setattr__(
            self, "_request_id", content_id(REQUEST_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_construction_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "catalogue_query_id": self.query.query_id,
            "model_selection_id": self.query.selection_id,
            "context_id": self.query.context_id,
            "topology_id": self.query.topology_id,
            "reason": "MODEL_MISS_NO_REGISTERED_WORLD_MODEL",
            "activation_state": "PREPARED_NO_ACCESS",
            "next_required_action": (
                "ENTER_OBSERVATION_DRIVEN_CONSTRUCTION_AND_CERTIFICATE_PIPELINE"
            ),
            "nearby_model_transfer_allowed": False,
            "ground_access_authorized_here": False,
            "observer_call_count": 0,
            "ground_draw_count": 0,
            "abstract_planner_invocations": 0,
            "plan_certificate_issued": False,
            "direct_fallback_executed_here": False,
        }

    @property
    def request_id(self) -> str:
        current = content_id(REQUEST_DOMAIN, self._payload())
        if current != self._request_id:
            _fail("catalogue construction request changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "construction_request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class HeldoutCatalogueAbstractPlanV1:
    _issuer: InitVar[object]
    query: HeldoutCatalogueQueryV1
    entry: catalogue_v1.HeldoutReusableModelCatalogueEntryV1
    source_reuse_bytes_sha256: str
    audit: robust.RobustPlanAuditV1 = field(repr=False)
    _plan_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _PLAN_ISSUER
            or type(self.query) is not HeldoutCatalogueQueryV1
            or type(self.entry)
            is not catalogue_v1.HeldoutReusableModelCatalogueEntryV1
            or type(self.audit) is not robust.RobustPlanAuditV1
            or self.query.selection_outcome != "EXACT_MODEL_MATCH"
            or self.query.selected_entry_id != self.entry.entry_id
            or self.query.context_id != self.entry.context_id
            or self.query.topology_id != self.entry.topology_id
            or self.source_reuse_bytes_sha256 != self.entry.source_reuse_bytes_sha256
            or self.audit.status is not robust.RobustAuditStatus.CERTIFIED
            or self.audit.solver_kind is not robust.RobustSolverKind.QUOTIENT
            or self.audit.model_id != self.entry.quotient_model_id
            or self.audit.threshold_profile_id != self.entry.threshold_profile_id
            or self.audit.audit_id != self.entry.certified_audit_id
        ):
            _fail("catalogue plan crossed its exact selected model")
        _cid(self.source_reuse_bytes_sha256, "selected reuse digest")
        object.__setattr__(self, "_plan_id", content_id(PLAN_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_abstract_plan.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "catalogue_query_id": self.query.query_id,
            "model_catalogue_entry_id": self.entry.entry_id,
            "source_reuse_result_id": self.entry.source_reuse_result_id,
            "source_overlay_id": self.entry.source_overlay_id,
            "source_reuse_bytes_sha256": self.source_reuse_bytes_sha256,
            "quotient_model_id": self.audit.model_id,
            "threshold_profile_id": self.audit.threshold_profile_id,
            "audit_id": self.audit.audit_id,
            "audit_status": self.audit.status.value,
            "abstract_planner_invocations": 1,
            "model_construction_invocations": 0,
            "observer_call_count": 0,
            "ground_draw_count": 0,
            "ground_solver_invocations": 0,
            "multi_step_plan_formed_in_selected_abstract_model": True,
            "conditional_statistical_plan_certificate_issued": True,
            "formal_exact_iid_plan_certificate": False,
        }

    @property
    def plan_id(self) -> str:
        current = content_id(PLAN_DOMAIN, self._payload())
        if current != self._plan_id:
            _fail("catalogue abstract plan changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit": self.audit.to_document(), "plan_id": self.plan_id}


@dataclass(frozen=True, slots=True)
class HeldoutCatalogueQueryResultV1:
    _issuer: InitVar[object]
    selection: catalogue_v1.HeldoutReusableModelSelectionV1
    query: HeldoutCatalogueQueryV1
    plan: HeldoutCatalogueAbstractPlanV1 | None
    construction_request: HeldoutCatalogueConstructionRequestV1 | None
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        hit = self.selection.outcome == "EXACT_MODEL_MATCH"
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.selection)
            is not catalogue_v1.HeldoutReusableModelSelectionV1
            or type(self.query) is not HeldoutCatalogueQueryV1
            or self.query.selection_id != self.selection.selection_id
            or self.query.selection_outcome != self.selection.outcome
            or (hit and (type(self.plan) is not HeldoutCatalogueAbstractPlanV1 or self.construction_request is not None))
            or ((not hit) and (self.plan is not None or type(self.construction_request) is not HeldoutCatalogueConstructionRequestV1))
        ):
            _fail("catalogue query result branch changed")
        if self.plan is not None and self.plan.query != self.query:
            _fail("catalogue plan crossed its frozen query")
        if self.construction_request is not None and self.construction_request.query != self.query:
            _fail("construction request crossed its frozen query")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        hit = self.plan is not None
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_query_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "model_selection_id": self.selection.selection_id,
            "catalogue_query_id": self.query.query_id,
            "routing_outcome": "ABSTRACT_PLAN_CERTIFIED" if hit else "CONSTRUCTION_REQUIRED",
            "plan_id": None if self.plan is None else self.plan.plan_id,
            "construction_request_id": (
                None if self.construction_request is None else self.construction_request.request_id
            ),
            "selected_model_catalogue_entry_id": self.selection.selected_entry_id,
            "selected_quotient_model_id": self.selection.selected_model_id,
            "abstract_planner_invocations": 1 if hit else 0,
            "model_construction_invocations": 0,
            "observer_call_count": 0,
            "ground_draw_count": 0,
            "ground_solver_invocations": 0,
            "cross_structural_model_transfer_attempted": False,
            "local_ground_recovery_executed_here": False,
            "direct_fallback_executed_here": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("catalogue query result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "selection": self.selection.to_document(),
            "query": self.query.to_document(),
            "plan": None if self.plan is None else self.plan.to_document(),
            "construction_request": (
                None
                if self.construction_request is None
                else self.construction_request.to_document()
            ),
            "catalogue_query_result_id": self.result_id,
        }


def _entry_for_selection(
    catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1,
    selection: catalogue_v1.HeldoutReusableModelSelectionV1,
) -> catalogue_v1.HeldoutReusableModelCatalogueEntryV1:
    matches = tuple(
        item for item in catalogue.entries if item.entry_id == selection.selected_entry_id
    )
    if len(matches) != 1:
        _fail("exact model selection does not resolve to one catalogue entry")
    return matches[0]


def _selected_model_and_threshold(
    entry: catalogue_v1.HeldoutReusableModelCatalogueEntryV1,
    reuse_result_bytes: bytes,
) -> tuple[robust.PartialSupportIntervalModelV1, robust.RobustThresholdProfileV1]:
    if type(reuse_result_bytes) is not bytes:
        _fail("exact catalogue hit requires canonical selected reuse bytes")
    try:
        document = loads_canonical_json(reuse_result_bytes)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCatalogueQueryRouterV1Error(
            "selected reuse result is not canonical JSON"
        ) from error
    if (
        type(document) is not dict
        or canonical_json_bytes(document) != reuse_result_bytes
        or hashlib.sha256(reuse_result_bytes).hexdigest()
        != entry.source_reuse_bytes_sha256
        or document.get("result_id") != entry.source_reuse_result_id
    ):
        _fail("selected reuse bytes differ from the catalogued immutable source")
    expected_schema = {
        "W5": "acfqp.construction_k7_heldout_abstract_reuse_result.v1",
        "K6": "acfqp.construction_k7_heldout_k6_abstract_reuse_result.v1",
    }[entry.family_key]
    source = document.get("source_result")
    model_document = document.get("final_quotient_model")
    threshold_document = document.get("threshold")
    if (
        document.get("schema") != expected_schema
        or type(source) is not dict
        or type(model_document) is not dict
        or type(threshold_document) is not dict
        or source.get("result_id") != entry.source_result_id
        or source.get("final_overlay_id") != entry.source_overlay_id
        or source.get("target_context_id") != entry.context_id
        or source.get("final_quotient_model_id") != entry.quotient_model_id
        or source.get("final_audit_id") != entry.certified_audit_id
        or model_document.get("model_id") != entry.quotient_model_id
        or threshold_document.get("threshold_profile_id")
        != entry.threshold_profile_id
    ):
        _fail("selected reuse structural chain differs from its catalogue entry")
    model = robust.replay_partial_support_interval_model_bytes_v1(
        canonical_json_bytes(model_document)
    )
    threshold = robust.replay_robust_threshold_profile_bytes_v1(
        canonical_json_bytes(threshold_document)
    )
    if model.context_id != entry.context_id or threshold.context_id != entry.context_id:
        _fail("selected model or threshold crossed its public context")
    return model, threshold


def run_heldout_catalogue_query_v1(
    catalogue: catalogue_v1.HeldoutReusableModelCatalogueV1,
    context: observer_v1.PublicGraphContextV1,
    *,
    logical_occurrence_id: str,
    occurrence_ordinal: int,
    selected_reuse_result_bytes: bytes | None,
) -> HeldoutCatalogueQueryResultV1:
    """Route a frozen query to one abstract plan or one no-access miss."""

    catalogue_v1.verify_heldout_reusable_model_catalogue_v1(catalogue)
    selection = catalogue_v1.select_heldout_reusable_model_v1(catalogue, context)
    query = HeldoutCatalogueQueryV1(
        _QUERY_ISSUER,
        catalogue.catalogue_id,
        selection.selection_id,
        _cid(logical_occurrence_id, "logical occurrence"),
        occurrence_ordinal,
        context.context_key,
        context.context_id,
        context.topology.topology_id,
        selection.outcome,
        selection.selected_entry_id,
    )
    if selection.outcome == "MODEL_MISS":
        if selected_reuse_result_bytes is not None:
            _fail("catalogue miss must not receive nearby model bytes")
        request = HeldoutCatalogueConstructionRequestV1(_REQUEST_ISSUER, query)
        return HeldoutCatalogueQueryResultV1(
            _RESULT_ISSUER, selection, query, None, request
        )

    entry = _entry_for_selection(catalogue, selection)
    if selected_reuse_result_bytes is None:
        _fail("exact catalogue hit is missing its immutable selected model bytes")
    model, threshold = _selected_model_and_threshold(
        entry, selected_reuse_result_bytes
    )
    audit = robust.solve_quotient_robust_h2_v1(model, threshold)
    plan = HeldoutCatalogueAbstractPlanV1(
        _PLAN_ISSUER,
        query,
        entry,
        hashlib.sha256(selected_reuse_result_bytes).hexdigest(),
        audit,
    )
    return HeldoutCatalogueQueryResultV1(
        _RESULT_ISSUER, selection, query, plan, None
    )


def verify_heldout_catalogue_query_result_v1(
    result: HeldoutCatalogueQueryResultV1,
    *,
    selected_reuse_result_bytes: bytes | None,
) -> HeldoutCatalogueQueryResultV1:
    """Revalidate one owner-bound result; hit verification replays its audit."""

    if type(result) is not HeldoutCatalogueQueryResultV1:
        _fail("catalogue query verifier rejects foreign values")
    result.__post_init__(_RESULT_ISSUER)
    if result.plan is None:
        if selected_reuse_result_bytes is not None:
            _fail("construction-required result cannot consume model bytes")
        return result
    if selected_reuse_result_bytes is None:
        _fail("abstract plan verification requires selected model bytes")
    model, threshold = _selected_model_and_threshold(
        result.plan.entry, selected_reuse_result_bytes
    )
    verification = robust.verify_robust_plan_audit_v1(
        model, threshold, result.plan.audit
    )
    if verification.audit_id != result.plan.audit.audit_id:
        _fail("catalogue abstract plan replay changed")
    return result


__all__ = (
    "ConstructionK7HeldoutCatalogueQueryRouterV1Error",
    "HeldoutCatalogueAbstractPlanV1",
    "HeldoutCatalogueConstructionRequestV1",
    "HeldoutCatalogueQueryResultV1",
    "HeldoutCatalogueQueryV1",
    "LOCAL_DOMAINS",
    "run_heldout_catalogue_query_v1",
    "verify_heldout_catalogue_query_result_v1",
)
