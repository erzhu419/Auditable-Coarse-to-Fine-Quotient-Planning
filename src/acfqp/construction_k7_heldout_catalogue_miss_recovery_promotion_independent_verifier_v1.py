"""Producer-free replay of the catalogue miss/recovery/promotion campaign."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Mapping, NoReturn

from acfqp import construction_k7_heldout_overlay_abstract_reuse_independent_verifier_v1 as w5_verifier
from acfqp import construction_k7_heldout_k6_overlay_abstract_reuse_independent_verifier_v1 as k6_verifier
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_CONSTRUCTION_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_EVENT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_ENTRY_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_MODEL_SELECTION_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.139"
PROFILE_KEY = (
    "construction_k7_heldout_catalogue_miss_recovery_promotion_"
    "independent_verifier_v1"
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_INDEPENDENT_VERIFICATION_V1_DOMAIN
)

PREREGISTRATION_FILENAME = "0001_PREREGISTRATION.json"
K6_REUSE_FILENAME = "0002_K6_REUSE_RESULT.json"
PROMOTION_FILENAME = "0003_MODEL_PROMOTION.json"
FINAL_ROUTE_FILENAME = "0004_FINAL_ABSTRACT_ROUTE.json"
CLOSURE_FILENAME = "0005_CAMPAIGN_CLOSURE.json"
EXPECTED_FILENAMES = (
    PREREGISTRATION_FILENAME,
    K6_REUSE_FILENAME,
    PROMOTION_FILENAME,
    FINAL_ROUTE_FILENAME,
    CLOSURE_FILENAME,
)

_CATALOGUE_CONTRACT = "2.0.136"
_CATALOGUE_PROFILE = "construction_k7_heldout_reusable_model_catalogue_v1"
_ROUTER_CONTRACT = "2.0.137"
_ROUTER_PROFILE = "construction_k7_heldout_catalogue_query_router_v1"
_CAMPAIGN_CONTRACT = "2.0.138"
_CAMPAIGN_PROFILE = "construction_k7_heldout_catalogue_miss_recovery_promotion_v1"


class ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error(
    ValueError
):
    """The portable campaign graph, model replay, or physical bytes changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{label} must be one object")
    return value


def _exact(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    if set(value) != keys:
        _fail(f"{label} fields changed")


def _domain(
    document: dict[str, Any],
    *,
    domain: str,
    id_key: str,
    keys: set[str],
    nested: set[str] = frozenset(),
    label: str,
) -> dict[str, Any]:
    _exact(document, keys, label)
    identity = _cid(document[id_key], f"{label} ID")
    payload = {
        key: value
        for key, value in document.items()
        if key != id_key and key not in nested
    }
    if content_id(domain, payload) != identity:
        _fail(f"{label} content ID changed")
    return payload


_ENTRY_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "family_key", "source_vertex_counts", "target_context_key",
    "target_vertex_count", "context_id", "topology_id", "source_result_id",
    "source_overlay_id", "quotient_model_id", "threshold_profile_id",
    "certified_audit_id", "source_reuse_result_id", "source_reuse_bytes_sha256",
    "source_independent_verification_id", "query_neutral_model",
    "source_certificate_failure_recovery_present",
    "fresh_zero_ground_abstract_reuse_verified",
    "selection_requires_exact_context_and_topology_identity",
    "cross_structural_model_transfer_allowed", "official_execution_allowed",
    "model_catalogue_entry_id",
}
_CATALOGUE_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "ordered_entry_ids", "registered_structural_context_keys",
    "registered_target_vertex_counts", "registered_model_count", "selector_kind",
    "nearby_structure_transfer_allowed", "model_miss_requires_new_construction_or_fallback",
    "persistent_storage_implemented", "official_execution_allowed",
    "model_catalogue_id",
}
_SELECTION_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "model_catalogue_id", "requested_context_key", "requested_context_id",
    "requested_topology_id", "requested_vertex_count", "selection_outcome",
    "selected_model_catalogue_entry_id", "selected_quotient_model_id",
    "selected_source_overlay_id", "exact_identity_match_required",
    "cross_structural_model_transfer_attempted", "fresh_ground_or_observer_event_count",
    "plan_certificate_issued", "local_ground_recovery_authorized_here",
    "direct_fallback_executed_here", "official_execution_allowed", "model_selection_id",
}
_QUERY_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "model_catalogue_id", "model_selection_id", "logical_occurrence_id",
    "occurrence_ordinal", "context_key", "context_id", "topology_id", "horizon",
    "selection_outcome", "selected_model_catalogue_entry_id",
    "query_frozen_before_model_replay_or_planning", "observer_or_ground_input_present",
    "catalogue_query_id",
}
_REQUEST_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "catalogue_query_id", "model_selection_id", "context_id", "topology_id",
    "reason", "activation_state", "next_required_action",
    "nearby_model_transfer_allowed", "ground_access_authorized_here",
    "observer_call_count", "ground_draw_count", "abstract_planner_invocations",
    "plan_certificate_issued", "direct_fallback_executed_here",
    "construction_request_id",
}
_PLAN_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "catalogue_query_id", "model_catalogue_entry_id", "source_reuse_result_id",
    "source_overlay_id", "source_reuse_bytes_sha256", "quotient_model_id",
    "threshold_profile_id", "audit_id", "audit_status",
    "abstract_planner_invocations", "model_construction_invocations",
    "observer_call_count", "ground_draw_count", "ground_solver_invocations",
    "multi_step_plan_formed_in_selected_abstract_model",
    "conditional_statistical_plan_certificate_issued",
    "formal_exact_iid_plan_certificate", "audit", "plan_id",
}
_ROUTE_RESULT_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "model_selection_id", "catalogue_query_id", "routing_outcome", "plan_id",
    "construction_request_id", "selected_model_catalogue_entry_id",
    "selected_quotient_model_id", "abstract_planner_invocations",
    "model_construction_invocations", "observer_call_count", "ground_draw_count",
    "ground_solver_invocations", "cross_structural_model_transfer_attempted",
    "local_ground_recovery_executed_here", "direct_fallback_executed_here",
    "official_execution_allowed", "selection", "query", "plan",
    "construction_request", "catalogue_query_result_id",
}
_PREREG_PAYLOAD_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "initial_model_catalogue_id", "initial_model_count", "initial_model_selection_id",
    "initial_catalogue_query_id", "initial_construction_request_id",
    "target_context_key", "target_context_id", "target_topology_id",
    "registered_validation_checkpoint_ladder", "max_local_transactions",
    "construction_must_follow_preregistration_commit",
    "local_ground_only_after_failed_abstract_certificate",
    "promoted_entry_requires_independent_reuse_verification",
    "nearby_model_transfer_allowed", "full_target_closure_authorized",
    "exact_evaluation_or_ground_solver_authorized", "official_execution_allowed",
}
_PREREG_KEYS = _PREREG_PAYLOAD_KEYS | {
    "initial_catalogue", "initial_miss", "w5_reuse_result",
    "promotion_preregistration_id",
}
_PROMOTION_PAYLOAD_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "promotion_preregistration_id", "initial_model_catalogue_id",
    "source_recertification_result_id", "source_base_audit_id",
    "source_base_audit_status", "source_recovery_request_id", "source_overlay_id",
    "source_final_audit_id", "source_final_audit_status",
    "source_changed_row_binding_ids", "source_changed_row_count",
    "source_preserved_row_count", "source_incremental_local_ground_draw_count",
    "source_full_16384_row_closure_built", "source_exact_evaluation_calls",
    "source_ground_solver_invocations", "source_reuse_result_id",
    "promoted_model_catalogue_entry_id", "promoted_quotient_model_id",
    "promoted_model_catalogue_id", "promoted_model_count",
    "request_frozen_before_local_observation",
    "local_ground_triggered_only_by_failed_certificate",
    "immutable_query_neutral_overlay_promoted",
    "independent_reuse_verification_required_before_promotion",
    "automatic_coordinate_primitive_invention_claimed", "official_execution_allowed",
}
_PROMOTION_KEYS = _PROMOTION_PAYLOAD_KEYS | {
    "promoted_entry", "promoted_catalogue", "model_promotion_id"
}
_COMMIT_KEYS = {"filename", "byte_count", "bytes_sha256"}
_CLOSURE_KEYS = {
    "schema", "schema_version", "proposed_contract_version", "profile_key",
    "promotion_preregistration_id", "model_promotion_id",
    "final_catalogue_query_result_id", "initial_model_catalogue_id",
    "promoted_model_catalogue_id", "ordered_predecessor_file_commits",
    "logical_occurrence_denominator", "certificate_coverage_denominator",
    "future_economics_cost_denominator", "plan_certificate_count",
    "infeasibility_certificate_count", "noncertificate_count",
    "initial_catalogue_miss_count", "local_recovery_transaction_count",
    "historical_local_ground_draw_count", "fresh_postpromotion_ground_draw_count",
    "fresh_postpromotion_observer_call_count",
    "fresh_postpromotion_abstract_planner_invocations",
    "multi_step_plan_mainly_completed_in_reusable_abstract_model",
    "ground_distinctions_restored_only_after_certificate_failure",
    "promoted_model_reusable_for_later_queries",
    "broad_cross_domain_generalization_claimed", "official_execution_allowed",
    "official_scalar_cost", "official_N_break_even",
    "counter_completeness_gate_status", "workload_economics_gate_status",
    "campaign_closure_id",
}


def _entry_document(
    family: str,
    reuse_bytes: bytes,
    verification_id: str,
) -> dict[str, Any]:
    reuse = _mapping(loads_canonical_json(reuse_bytes), f"{family} reuse")
    source = _mapping(reuse["source_result"], f"{family} source")
    query = _mapping(reuse["query"], f"{family} query")
    plan = _mapping(reuse["plan"], f"{family} plan")
    model = _mapping(reuse["final_quotient_model"], f"{family} model")
    threshold = _mapping(reuse["threshold"], f"{family} threshold")
    context_key, vertex_count = (
        ("opaque_graph_w5_v0", 5) if family == "W5" else ("opaque_graph_k6_v0", 6)
    )
    context = observer_v1.public_context_by_key_v1(context_key)
    payload = {
        "schema": "acfqp.construction_k7_heldout_model_catalogue_entry.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": _CATALOGUE_CONTRACT,
        "profile_key": _CATALOGUE_PROFILE,
        "family_key": family,
        "source_vertex_counts": [4],
        "target_context_key": context_key,
        "target_vertex_count": vertex_count,
        "context_id": source["target_context_id"],
        "topology_id": context.topology.topology_id,
        "source_result_id": source["result_id"],
        "source_overlay_id": source["final_overlay_id"],
        "quotient_model_id": query["quotient_model_id"],
        "threshold_profile_id": query["threshold_profile_id"],
        "certified_audit_id": plan["replanned_audit_id"],
        "source_reuse_result_id": reuse["result_id"],
        "source_reuse_bytes_sha256": hashlib.sha256(reuse_bytes).hexdigest(),
        "source_independent_verification_id": verification_id,
        "query_neutral_model": True,
        "source_certificate_failure_recovery_present": True,
        "fresh_zero_ground_abstract_reuse_verified": True,
        "selection_requires_exact_context_and_topology_identity": True,
        "cross_structural_model_transfer_allowed": False,
        "official_execution_allowed": False,
    }
    if (
        model["model_id"] != payload["quotient_model_id"]
        or threshold["threshold_profile_id"] != payload["threshold_profile_id"]
        or source["final_quotient_model_id"] != payload["quotient_model_id"]
        or source["final_audit_id"] != payload["certified_audit_id"]
    ):
        _fail(f"{family} catalogue entry crossed its verified reuse result")
    return {
        **payload,
        "model_catalogue_entry_id": content_id(
            CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_ENTRY_V1_DOMAIN, payload
        ),
    }


def _catalogue_document(entries: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.construction_k7_heldout_model_catalogue.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": _CATALOGUE_CONTRACT,
        "profile_key": _CATALOGUE_PROFILE,
        "ordered_entry_ids": [item["model_catalogue_entry_id"] for item in entries],
        "registered_structural_context_keys": [item["target_context_key"] for item in entries],
        "registered_target_vertex_counts": [item["target_vertex_count"] for item in entries],
        "registered_model_count": len(entries),
        "selector_kind": "EXACT_CONTEXT_AND_TOPOLOGY_IDENTITY",
        "nearby_structure_transfer_allowed": False,
        "model_miss_requires_new_construction_or_fallback": True,
        "persistent_storage_implemented": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "model_catalogue_id": content_id(
            CONSTRUCTION_K7_HELDOUT_MODEL_CATALOGUE_V1_DOMAIN, payload
        ),
    }


def _selection_document(
    catalogue_id: str,
    context: observer_v1.PublicGraphContextV1,
    entry: dict[str, Any] | None,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.construction_k7_heldout_model_selection.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": _CATALOGUE_CONTRACT,
        "profile_key": _CATALOGUE_PROFILE,
        "model_catalogue_id": catalogue_id,
        "requested_context_key": context.context_key,
        "requested_context_id": context.context_id,
        "requested_topology_id": context.topology.topology_id,
        "requested_vertex_count": context.topology.vertex_count,
        "selection_outcome": "MODEL_MISS" if entry is None else "EXACT_MODEL_MATCH",
        "selected_model_catalogue_entry_id": None if entry is None else entry["model_catalogue_entry_id"],
        "selected_quotient_model_id": None if entry is None else entry["quotient_model_id"],
        "selected_source_overlay_id": None if entry is None else entry["source_overlay_id"],
        "exact_identity_match_required": True,
        "cross_structural_model_transfer_attempted": False,
        "fresh_ground_or_observer_event_count": 0,
        "plan_certificate_issued": False,
        "local_ground_recovery_authorized_here": False,
        "direct_fallback_executed_here": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "model_selection_id": content_id(
            CONSTRUCTION_K7_HELDOUT_MODEL_SELECTION_V1_DOMAIN, payload
        ),
    }


def _verify_query(
    query: dict[str, Any],
    *,
    catalogue_id: str,
    selection: dict[str, Any],
    context: observer_v1.PublicGraphContextV1,
    entry: dict[str, Any] | None,
) -> None:
    _domain(
        query,
        domain=CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_V1_DOMAIN,
        id_key="catalogue_query_id",
        keys=_QUERY_KEYS,
        label="catalogue query",
    )
    if (
        query["schema"] != "acfqp.construction_k7_heldout_catalogue_query.v1"
        or query["schema_version"] != "1.0.0"
        or query["proposed_contract_version"] != _ROUTER_CONTRACT
        or query["profile_key"] != _ROUTER_PROFILE
        or query["model_catalogue_id"] != catalogue_id
        or query["model_selection_id"] != selection["model_selection_id"]
        or query["context_key"] != context.context_key
        or query["context_id"] != context.context_id
        or query["topology_id"] != context.topology.topology_id
        or query["horizon"] != 2
        or type(query["occurrence_ordinal"]) is not int
        or query["occurrence_ordinal"] <= 0
        or query["selection_outcome"] != selection["selection_outcome"]
        or query["selected_model_catalogue_entry_id"]
        != (None if entry is None else entry["model_catalogue_entry_id"])
        or query["query_frozen_before_model_replay_or_planning"] is not True
        or query["observer_or_ground_input_present"] is not False
    ):
        _fail("catalogue query semantics changed")


def _verify_route(
    route: dict[str, Any],
    *,
    catalogue: dict[str, Any],
    context: observer_v1.PublicGraphContextV1,
    entry: dict[str, Any] | None,
    model: robust.PartialSupportIntervalModelV1 | None = None,
    threshold: robust.RobustThresholdProfileV1 | None = None,
) -> robust.RobustPlanAuditV1 | None:
    _domain(
        route,
        domain=CONSTRUCTION_K7_HELDOUT_CATALOGUE_QUERY_RESULT_V1_DOMAIN,
        id_key="catalogue_query_result_id",
        keys=_ROUTE_RESULT_KEYS,
        nested={"selection", "query", "plan", "construction_request"},
        label="catalogue query result",
    )
    selection = _mapping(route["selection"], "model selection")
    expected_selection = _selection_document(
        catalogue["model_catalogue_id"], context, entry
    )
    _exact(selection, _SELECTION_KEYS, "model selection")
    if canonical_json_bytes(selection) != canonical_json_bytes(expected_selection):
        _fail("model selection differs from exact structural replay")
    query = _mapping(route["query"], "catalogue query")
    _verify_query(
        query,
        catalogue_id=catalogue["model_catalogue_id"],
        selection=selection,
        context=context,
        entry=entry,
    )
    hit = entry is not None
    if (
        route["model_selection_id"] != selection["model_selection_id"]
        or route["catalogue_query_id"] != query["catalogue_query_id"]
        or route["routing_outcome"]
        != ("ABSTRACT_PLAN_CERTIFIED" if hit else "CONSTRUCTION_REQUIRED")
        or route["abstract_planner_invocations"] != (1 if hit else 0)
        or route["model_construction_invocations"] != 0
        or route["observer_call_count"] != 0
        or route["ground_draw_count"] != 0
        or route["ground_solver_invocations"] != 0
        or route["cross_structural_model_transfer_attempted"] is not False
        or route["local_ground_recovery_executed_here"] is not False
        or route["direct_fallback_executed_here"] is not False
        or route["official_execution_allowed"] is not False
    ):
        _fail("catalogue route claim locks changed")
    if not hit:
        request = _mapping(route["construction_request"], "construction request")
        _domain(
            request,
            domain=CONSTRUCTION_K7_HELDOUT_CATALOGUE_CONSTRUCTION_REQUEST_V1_DOMAIN,
            id_key="construction_request_id",
            keys=_REQUEST_KEYS,
            label="construction request",
        )
        if (
            route["plan"] is not None
            or route["plan_id"] is not None
            or route["construction_request_id"] != request["construction_request_id"]
            or request["catalogue_query_id"] != query["catalogue_query_id"]
            or request["reason"] != "MODEL_MISS_NO_REGISTERED_WORLD_MODEL"
            or request["activation_state"] != "PREPARED_NO_ACCESS"
            or request["ground_access_authorized_here"] is not False
            or request["abstract_planner_invocations"] != 0
            or request["plan_certificate_issued"] is not False
        ):
            _fail("catalogue miss request changed")
        return None
    if model is None or threshold is None:
        _fail("exact hit lacks its independently rebuilt model")
    plan = _mapping(route["plan"], "catalogue abstract plan")
    _domain(
        plan,
        domain=CONSTRUCTION_K7_HELDOUT_CATALOGUE_ABSTRACT_PLAN_V1_DOMAIN,
        id_key="plan_id",
        keys=_PLAN_KEYS,
        nested={"audit"},
        label="catalogue abstract plan",
    )
    audit = robust.solve_quotient_robust_h2_v1(model, threshold)
    if (
        audit.status is not robust.RobustAuditStatus.CERTIFIED
        or canonical_json_bytes(plan["audit"]) != canonical_json_bytes(audit.to_document())
        or plan["catalogue_query_id"] != query["catalogue_query_id"]
        or plan["model_catalogue_entry_id"] != entry["model_catalogue_entry_id"]
        or plan["source_reuse_result_id"] != entry["source_reuse_result_id"]
        or plan["source_overlay_id"] != entry["source_overlay_id"]
        or plan["source_reuse_bytes_sha256"] != entry["source_reuse_bytes_sha256"]
        or plan["quotient_model_id"] != model.model_id
        or plan["threshold_profile_id"] != threshold.threshold_profile_id
        or plan["audit_id"] != audit.audit_id
        or plan["audit_status"] != "CERTIFIED"
        or plan["abstract_planner_invocations"] != 1
        or plan["model_construction_invocations"] != 0
        or plan["observer_call_count"] != 0
        or plan["ground_draw_count"] != 0
        or plan["ground_solver_invocations"] != 0
        or plan["multi_step_plan_formed_in_selected_abstract_model"] is not True
        or plan["conditional_statistical_plan_certificate_issued"] is not True
        or plan["formal_exact_iid_plan_certificate"] is not False
        or route["plan_id"] != plan["plan_id"]
        or route["construction_request"] is not None
        or route["construction_request_id"] is not None
    ):
        _fail("catalogue abstract plan differs from independent replay")
    return audit


@dataclass(frozen=True, slots=True)
class CataloguePromotionDirectoryVerificationV1:
    preregistration_id: str
    w5_verification_id: str
    k6_verification_id: str
    promotion_id: str
    final_route_result_id: str
    closure_id: str
    verification_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.preregistration_id, "verified preregistration"),
            (self.w5_verification_id, "W5 verification"),
            (self.k6_verification_id, "K6 verification"),
            (self.promotion_id, "verified promotion"),
            (self.final_route_result_id, "verified final route"),
            (self.closure_id, "verified closure"),
            (self.verification_id, "campaign verification"),
        ):
            _cid(value, label)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_catalogue_promotion_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "promotion_preregistration_id": self.preregistration_id,
            "w5_reuse_independent_verification_id": self.w5_verification_id,
            "k6_reuse_independent_verification_id": self.k6_verification_id,
            "model_promotion_id": self.promotion_id,
            "final_catalogue_query_result_id": self.final_route_result_id,
            "campaign_closure_id": self.closure_id,
            "producer_import_count": 0,
            "initial_miss_independently_replayed": True,
            "k6_local_recovery_independently_replayed": True,
            "catalogue_epoch_promotion_independently_replayed": True,
            "fresh_postpromotion_abstract_plan_independently_replayed": True,
            "physical_campaign_bytes_verified": True,
            "valid": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _read(directory: Path, filename: str) -> tuple[bytes, dict[str, Any]]:
    target = directory / filename
    if target.is_symlink() or not target.is_file():
        _fail(f"campaign {filename} is absent or non-regular")
    raw = target.read_bytes()
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error(
            f"campaign {filename} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"campaign {filename} is not one canonical object")
    return raw, document


def verify_catalogue_promotion_campaign_directory_bytes_v1(
    campaign_directory: str | Path,
) -> CataloguePromotionDirectoryVerificationV1:
    directory = Path(campaign_directory)
    raws: dict[str, bytes] = {}
    documents: dict[str, dict[str, Any]] = {}
    for filename in EXPECTED_FILENAMES:
        raw, document = _read(directory, filename)
        raws[filename] = raw
        documents[filename] = document

    prereg = documents[PREREGISTRATION_FILENAME]
    _domain(
        prereg,
        domain=CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_PREREGISTRATION_V1_DOMAIN,
        id_key="promotion_preregistration_id",
        keys=_PREREG_KEYS,
        nested={"initial_catalogue", "initial_miss", "w5_reuse_result"},
        label="promotion preregistration",
    )
    if (
        prereg["schema"] != "acfqp.construction_k7_heldout_catalogue_promotion_preregistration.v1"
        or prereg["schema_version"] != "1.0.0"
        or prereg["proposed_contract_version"] != _CAMPAIGN_CONTRACT
        or prereg["profile_key"] != _CAMPAIGN_PROFILE
    ):
        _fail("promotion preregistration profile changed")
    w5_document = _mapping(prereg["w5_reuse_result"], "W5 reuse result")
    w5_bytes = canonical_json_bytes(w5_document)
    w5_verification = w5_verifier.verify_heldout_overlay_abstract_reuse_bytes_v1(
        w5_bytes
    )
    w5_entry = _entry_document("W5", w5_bytes, w5_verification.verification_id)
    initial_catalogue = _catalogue_document([w5_entry])
    claimed_initial = _mapping(prereg["initial_catalogue"], "initial catalogue")
    _exact(claimed_initial, _CATALOGUE_KEYS, "initial catalogue")
    if canonical_json_bytes(claimed_initial) != canonical_json_bytes(initial_catalogue):
        _fail("initial catalogue differs from verified W5-only replay")
    k6_context = observer_v1.public_context_by_key_v1("opaque_graph_k6_v0")
    initial_miss = _mapping(prereg["initial_miss"], "initial catalogue miss")
    _verify_route(
        initial_miss,
        catalogue=initial_catalogue,
        context=k6_context,
        entry=None,
    )
    request = _mapping(initial_miss["construction_request"], "initial construction request")
    if (
        prereg["initial_model_catalogue_id"] != initial_catalogue["model_catalogue_id"]
        or prereg["initial_model_count"] != 1
        or prereg["initial_model_selection_id"] != initial_miss["model_selection_id"]
        or prereg["initial_catalogue_query_id"] != initial_miss["catalogue_query_id"]
        or prereg["initial_construction_request_id"] != request["construction_request_id"]
        or prereg["target_context_key"] != "opaque_graph_k6_v0"
        or prereg["target_context_id"] != k6_context.context_id
        or prereg["target_topology_id"] != k6_context.topology.topology_id
        or prereg["registered_validation_checkpoint_ladder"] != [8_192, 16_384]
        or prereg["max_local_transactions"] != 1
        or any(
            prereg[key] is not expected
            for key, expected in {
                "construction_must_follow_preregistration_commit": True,
                "local_ground_only_after_failed_abstract_certificate": True,
                "promoted_entry_requires_independent_reuse_verification": True,
                "nearby_model_transfer_allowed": False,
                "full_target_closure_authorized": False,
                "exact_evaluation_or_ground_solver_authorized": False,
                "official_execution_allowed": False,
            }.items()
        )
    ):
        _fail("promotion preregistration semantics changed")

    k6_bytes = raws[K6_REUSE_FILENAME]
    k6_document = documents[K6_REUSE_FILENAME]
    k6_verification = k6_verifier.verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
        k6_bytes
    )
    k6_entry = _entry_document("K6", k6_bytes, k6_verification.verification_id)
    promoted_catalogue = _catalogue_document([w5_entry, k6_entry])
    source = _mapping(k6_document["source_result"], "K6 source result")
    source_overlay = _mapping(source["overlay"], "K6 source overlay")

    promotion = documents[PROMOTION_FILENAME]
    _domain(
        promotion,
        domain=CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_EVENT_V1_DOMAIN,
        id_key="model_promotion_id",
        keys=_PROMOTION_KEYS,
        nested={"promoted_entry", "promoted_catalogue"},
        label="model promotion",
    )
    _exact(_mapping(promotion["promoted_entry"], "promoted entry"), _ENTRY_KEYS, "promoted entry")
    _exact(_mapping(promotion["promoted_catalogue"], "promoted catalogue"), _CATALOGUE_KEYS, "promoted catalogue")
    if (
        canonical_json_bytes(promotion["promoted_entry"]) != canonical_json_bytes(k6_entry)
        or canonical_json_bytes(promotion["promoted_catalogue"]) != canonical_json_bytes(promoted_catalogue)
        or promotion["promotion_preregistration_id"] != prereg["promotion_preregistration_id"]
        or promotion["initial_model_catalogue_id"] != initial_catalogue["model_catalogue_id"]
        or promotion["source_recertification_result_id"] != source["result_id"]
        or promotion["source_base_audit_id"] != source["base_audit_id"]
        or promotion["source_base_audit_status"] != "FAILED_PROOF_FRONTIER"
        or promotion["source_recovery_request_id"] != source["recovery_request_id"]
        or promotion["source_overlay_id"] != source_overlay["overlay_id"]
        or promotion["source_final_audit_id"] != source_overlay["audit_id"]
        or promotion["source_final_audit_status"] != "CERTIFIED"
        or promotion["source_changed_row_binding_ids"] != source_overlay["changed_row_binding_ids"]
        or promotion["source_changed_row_count"] != 1
        or promotion["source_preserved_row_count"] != 19
        or promotion["source_incremental_local_ground_draw_count"] != 8_192
        or promotion["source_full_16384_row_closure_built"] is not False
        or promotion["source_exact_evaluation_calls"] != 0
        or promotion["source_ground_solver_invocations"] != 0
        or promotion["source_reuse_result_id"] != k6_document["result_id"]
        or promotion["promoted_model_catalogue_entry_id"] != k6_entry["model_catalogue_entry_id"]
        or promotion["promoted_quotient_model_id"] != k6_entry["quotient_model_id"]
        or promotion["promoted_model_catalogue_id"] != promoted_catalogue["model_catalogue_id"]
        or promotion["promoted_model_count"] != 2
        or any(
            promotion[key] is not expected
            for key, expected in {
                "request_frozen_before_local_observation": True,
                "local_ground_triggered_only_by_failed_certificate": True,
                "immutable_query_neutral_overlay_promoted": True,
                "independent_reuse_verification_required_before_promotion": True,
                "automatic_coordinate_primitive_invention_claimed": False,
                "official_execution_allowed": False,
            }.items()
        )
    ):
        _fail("model promotion differs from independently verified recovery")

    model = robust.replay_partial_support_interval_model_bytes_v1(
        canonical_json_bytes(k6_document["final_quotient_model"])
    )
    threshold = robust.replay_robust_threshold_profile_bytes_v1(
        canonical_json_bytes(k6_document["threshold"])
    )
    final_route = documents[FINAL_ROUTE_FILENAME]
    final_audit = _verify_route(
        final_route,
        catalogue=promoted_catalogue,
        context=k6_context,
        entry=k6_entry,
        model=model,
        threshold=threshold,
    )
    if final_audit is None:
        _fail("postpromotion route did not certify")

    predecessor_commits = [
        {
            "filename": filename,
            "byte_count": len(raws[filename]),
            "bytes_sha256": hashlib.sha256(raws[filename]).hexdigest(),
        }
        for filename in EXPECTED_FILENAMES[:4]
    ]
    closure = documents[CLOSURE_FILENAME]
    _domain(
        closure,
        domain=CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_CLOSURE_V1_DOMAIN,
        id_key="campaign_closure_id",
        keys=_CLOSURE_KEYS,
        label="campaign closure",
    )
    for item in closure["ordered_predecessor_file_commits"]:
        _exact(_mapping(item, "predecessor file commit"), _COMMIT_KEYS, "predecessor file commit")
    if (
        closure["promotion_preregistration_id"] != prereg["promotion_preregistration_id"]
        or closure["model_promotion_id"] != promotion["model_promotion_id"]
        or closure["final_catalogue_query_result_id"] != final_route["catalogue_query_result_id"]
        or closure["initial_model_catalogue_id"] != initial_catalogue["model_catalogue_id"]
        or closure["promoted_model_catalogue_id"] != promoted_catalogue["model_catalogue_id"]
        or closure["ordered_predecessor_file_commits"] != predecessor_commits
        or any(
            closure[key] != expected
            for key, expected in {
                "logical_occurrence_denominator": 1,
                "certificate_coverage_denominator": 1,
                "future_economics_cost_denominator": 1,
                "plan_certificate_count": 1,
                "infeasibility_certificate_count": 0,
                "noncertificate_count": 0,
                "initial_catalogue_miss_count": 1,
                "local_recovery_transaction_count": 1,
                "historical_local_ground_draw_count": 8_192,
                "fresh_postpromotion_ground_draw_count": 0,
                "fresh_postpromotion_observer_call_count": 0,
                "fresh_postpromotion_abstract_planner_invocations": 1,
                "multi_step_plan_mainly_completed_in_reusable_abstract_model": True,
                "ground_distinctions_restored_only_after_certificate_failure": True,
                "promoted_model_reusable_for_later_queries": True,
                "broad_cross_domain_generalization_claimed": False,
                "official_execution_allowed": False,
                "official_scalar_cost": None,
                "official_N_break_even": None,
                "counter_completeness_gate_status": "NOT_RUN",
                "workload_economics_gate_status": "NOT_RUN",
            }.items()
        )
    ):
        _fail("campaign closure or denominator changed")

    payload = {
        "schema": "acfqp.construction_k7_heldout_catalogue_promotion_independent_verification.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "promotion_preregistration_id": prereg["promotion_preregistration_id"],
        "w5_reuse_independent_verification_id": w5_verification.verification_id,
        "k6_reuse_independent_verification_id": k6_verification.verification_id,
        "model_promotion_id": promotion["model_promotion_id"],
        "final_catalogue_query_result_id": final_route["catalogue_query_result_id"],
        "campaign_closure_id": closure["campaign_closure_id"],
        "producer_import_count": 0,
        "initial_miss_independently_replayed": True,
        "k6_local_recovery_independently_replayed": True,
        "catalogue_epoch_promotion_independently_replayed": True,
        "fresh_postpromotion_abstract_plan_independently_replayed": True,
        "physical_campaign_bytes_verified": True,
        "valid": True,
    }
    verification_id = content_id(VERIFICATION_DOMAIN, payload)
    return CataloguePromotionDirectoryVerificationV1(
        prereg["promotion_preregistration_id"],
        w5_verification.verification_id,
        k6_verification.verification_id,
        promotion["model_promotion_id"],
        final_route["catalogue_query_result_id"],
        closure["campaign_closure_id"],
        verification_id,
    )


__all__ = (
    "CataloguePromotionDirectoryVerificationV1",
    "ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error",
    "EXPECTED_FILENAMES",
    "verify_catalogue_promotion_campaign_directory_bytes_v1",
)
