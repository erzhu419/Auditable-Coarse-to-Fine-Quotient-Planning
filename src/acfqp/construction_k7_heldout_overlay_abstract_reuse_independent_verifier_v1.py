"""Producer-free replay of held-out overlay reuse from canonical bytes.

This verifier deliberately imports neither held-out producer.  It validates
the content-addressed recovery chain, reconstructs the final interval model
and threshold from literal schemas, reruns the quotient solver, and checks the
fresh query/plan/result domains and zero-ground claim locks.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, NoReturn

from acfqp import partial_support_robust_planner_v1 as robust
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CAUSAL_ROW_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CHECKPOINT_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_COORDINATE_CHECKPOINT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_OVERLAY_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_OVERLAY_QUERY_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_RECERTIFICATION_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_VALIDATION_DELTA_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.121"
PROFILE_KEY = "construction_k7_heldout_overlay_abstract_reuse_independent_verifier_v1"
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_INDEPENDENT_VERIFICATION_V1_DOMAIN
)


class ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error(
    ValueError
):
    """Canonical bytes, artifact links, or independent audit replay failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error(
        message
    )


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{label} must be one canonical object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if type(value) is not list:
        _fail(f"{label} must be one canonical list")
    return value


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        _fail(f"{label} fields changed")


def _same_document(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _verify_domain_document(
    document: dict[str, Any],
    *,
    domain: str,
    identity_key: str,
    nested_keys: set[str] = frozenset(),
    expected_keys: set[str],
    label: str,
) -> dict[str, Any]:
    _exact_keys(document, expected_keys, label)
    expected_id = _cid(document[identity_key], f"{label} ID")
    payload = {
        key: value
        for key, value in document.items()
        if key != identity_key and key not in nested_keys
    }
    if content_id(domain, payload) != expected_id:
        _fail(f"{label} content ID changed")
    return payload


_PREREG_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "target_context_key", "target_context_id", "target_topology_id",
    "source_skeleton_id", "source_observation_log_id", "source_vertex_counts",
    "target_vertex_count", "validation_checkpoints", "max_local_transactions",
    "coordinate_candidate_rule", "coordinate_candidate_ordinal",
    "causal_selection_rule", "request_must_precede_new_observation",
    "full_target_closure_authorized", "evaluation_exact_kernel_authorized",
    "ground_solver_authorized", "preregistration_id",
}
_CHECKPOINT_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "preregistration_id", "closure_id", "base_bridge_id", "base_audit_id",
    "refinement_result_id", "candidate_spec_id", "coordinate_profile_id",
    "candidate_ordinal", "candidate_count", "failed_candidate_audit_ids",
    "base_outcome", "refinement_outcome", "complete_candidate_enumeration",
    "selected_using_future_checkpoint_data", "checkpoint_id",
}
_EVIDENCE_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "transaction_index", "checkpoint_id", "prior_overlay_id", "failed_audit_id",
    "failed_frontier_id", "excluded_row_binding_ids", "causal_candidates",
    "selected_planner_row_id", "selected_partial_row_id",
    "selected_row_binding_id", "selected_remaining_horizon", "selection_rule",
    "counterfactual_is_selection_only", "counterfactual_probability_evidence",
    "evidence_id",
}
_REQUEST_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "transaction_index", "preregistration_id", "causal_evidence_id",
    "row_binding_id", "before_partial_row_id", "from_validation_checkpoint",
    "to_validation_checkpoint", "authorized_incremental_draws",
    "request_frozen_before_new_observation", "single_row_only", "request_id",
}
_DELTA_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key", "request_id",
    "row_binding_id", "before_partial_row_id", "after_partial_row_id",
    "before_confidence_authority_id", "after_confidence_authority_id",
    "before_validation_checkpoint", "after_validation_checkpoint",
    "incremental_observer_draws", "incremental_random_word_calls",
    "incremental_rejections", "before_observation_prefix_digest",
    "after_observation_prefix_digest", "predecessor_is_exact_prefix",
    "request_frozen_before_new_observation", "delta_id",
}
_OVERLAY_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "transaction_index", "prior_overlay_id", "prior_bridge_id", "prior_model_id",
    "prior_audit_id", "delta_id", "changed_row_binding_ids",
    "preserved_row_binding_ids", "bridge_id", "quotient_model_id", "audit_id",
    "audit_status", "root_failure_upper", "normalized_regret_upper",
    "immutable_query_neutral_overlay", "abstract_planner_invocations",
    "ground_solver_invocations", "evaluation_exact_kernel_calls", "delta", "audit",
    "overlay_id",
}
_SOURCE_PAYLOAD_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "preregistration_id", "checkpoint_id", "target_context_id",
    "source_vertex_counts", "target_vertex_count", "base_bridge_id",
    "base_quotient_model_id", "base_audit_id", "base_audit_status",
    "transaction_evidence_ids", "recovery_request_ids", "validation_delta_ids",
    "overlay_ids", "overlay_audit_statuses", "final_overlay_id", "final_bridge_id",
    "final_quotient_model_id", "final_audit_id", "final_root_failure_upper",
    "final_normalized_regret_upper", "base_observer_draw_count",
    "incremental_local_ground_draw_count", "changed_row_binding_ids",
    "preserved_row_binding_ids", "changed_row_count", "preserved_row_count",
    "full_4096_row_closure_built", "rows_retained_at_base_checkpoint",
    "multi_step_plan_formed_in_abstract_model",
    "local_ground_restoration_only_after_certificate_failure",
    "query_neutral_overlay_reusable", "evaluation_exact_kernel_calls",
    "ground_solver_invocations", "coordinate_primitive_invention_count",
    "construction_certificate_status", "formal_exact_iid_plan_certificate",
    "heldout_family_scope", "broad_cross_domain_generalization_claimed",
    "official_execution_allowed", "scientific_endpoint_credit_allowed",
    "official_scalar_cost", "official_N_break_even",
    "counter_completeness_gate_status", "workload_economics_gate_status",
}
_SOURCE_KEYS = _SOURCE_PAYLOAD_KEYS | {
    "preregistration", "checkpoint", "transactions", "result_id"
}
_QUERY_PAYLOAD_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "logical_occurrence_id", "occurrence_ordinal", "source_result_id",
    "source_overlay_id", "context_id", "quotient_model_id",
    "threshold_profile_id", "horizon", "query_frozen_before_planner_invocation",
    "observer_or_ground_input_present", "exact_evaluation_input_present",
}
_QUERY_KEYS = _QUERY_PAYLOAD_KEYS | {"query_id"}
_PLAN_PAYLOAD_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key", "query_id",
    "source_audit_id", "replanned_audit_id", "quotient_model_id",
    "threshold_profile_id", "audit_status", "fresh_query_identity_outside_model_proof",
    "abstract_planner_invocations", "model_build_invocations", "new_ground_draw_count",
    "observer_call_count", "ground_solver_invocations", "evaluation_exact_kernel_calls",
    "multi_step_plan_formed_in_abstract_model",
}
_PLAN_KEYS = _PLAN_PAYLOAD_KEYS | {"audit", "plan_id"}
_RESULT_PAYLOAD_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "source_result_id", "source_overlay_id", "source_final_audit_id", "query_id",
    "plan_id", "replanned_audit_id", "fresh_occurrence_new_ground_draw_count",
    "fresh_occurrence_observer_call_count", "fresh_occurrence_ground_solver_invocations",
    "fresh_occurrence_evaluation_exact_kernel_calls",
    "fresh_occurrence_abstract_planner_invocations",
    "fresh_occurrence_directly_abstract_certified",
    "certificate_failure_triggered_local_recovery",
    "source_local_recovery_reused_as_query_neutral_overlay",
    "construction_certificate_status", "formal_exact_iid_plan_certificate",
    "official_execution_allowed", "scientific_endpoint_credit_allowed",
    "official_scalar_cost", "official_N_break_even",
    "counter_completeness_gate_status", "workload_economics_gate_status",
}
_RESULT_KEYS = _RESULT_PAYLOAD_KEYS | {
    "source_result", "query", "plan", "final_quotient_model", "threshold", "result_id"
}


def _rebuild_model(document: dict[str, Any]) -> robust.PartialSupportIntervalModelV1:
    catalogue_documents = _list(document.get("catalogues"), "model catalogues")
    destination_documents = _list(document.get("destinations"), "model destinations")
    row_documents = _list(document.get("rows"), "model rows")
    concretizer_documents = _list(
        document.get("concretizer_entries"), "model concretizers"
    )
    catalogues: list[robust.StateActionCatalogueV1] = []
    for raw in catalogue_documents:
        item = _mapping(raw, "model catalogue")
        actions: list[robust.CatalogueActionV1] = []
        for raw_action in _list(item.get("actions"), "catalogue actions"):
            action = _mapping(raw_action, "catalogue action")
            rebuilt_action = robust.CatalogueActionV1(
                action["action_id"], action["action_coordinate_key"]
            )
            if not _same_document(rebuilt_action.to_document(), action):
                _fail("catalogue action differs from literal replay")
            actions.append(rebuilt_action)
        rebuilt = robust.StateActionCatalogueV1(
            item["state_id"], item["state_coordinate_key"], tuple(actions)
        )
        if not _same_document(rebuilt.to_document(), item):
            _fail("state-action catalogue differs from literal replay")
        catalogues.append(rebuilt)
    destinations: list[robust.RegisteredDestinationV1] = []
    for raw in destination_documents:
        item = _mapping(raw, "model destination")
        rebuilt = robust.RegisteredDestinationV1(
            item["destination_id"],
            robust.DestinationCategory(item["category"]),
            item["state_id"],
        )
        if not _same_document(rebuilt.to_document(), item):
            _fail("destination differs from literal replay")
        destinations.append(rebuilt)
    rows: list[robust.IntervalSimplexRowV1] = []
    for raw in row_documents:
        item = _mapping(raw, "model row")
        masses: list[robust.IntervalDestinationMassV1] = []
        for raw_mass in _list(item.get("masses"), "row masses"):
            mass = _mapping(raw_mass, "row mass")
            rebuilt_mass = robust.IntervalDestinationMassV1(
                mass["destination_id"], mass["lower"], mass["upper"]
            )
            if not _same_document(rebuilt_mass.to_document(), mass):
                _fail("interval mass differs from literal replay")
            masses.append(rebuilt_mass)
        rebuilt = robust.IntervalSimplexRowV1(
            item["state_id"], item["remaining_horizon"], item["action_id"],
            item["reward_lower"], item["reward_upper"],
            item["other_destination_id"], tuple(masses),
        )
        if not _same_document(rebuilt.to_document(), item):
            _fail("interval row differs from literal replay")
        rows.append(rebuilt)
    concretizers: list[robust.DistinctActionConcretizerEntryV1] = []
    for raw in concretizer_documents:
        item = _mapping(raw, "model concretizer")
        rebuilt = robust.DistinctActionConcretizerEntryV1(
            item["state_coordinate_key"], item["state_id"],
            item["abstract_action_key"], tuple(item["ground_action_ids"]),
        )
        if not _same_document(rebuilt.to_document(), item):
            _fail("concretizer differs from literal replay")
        concretizers.append(rebuilt)
    model = robust.build_partial_support_model_v1(
        context_id=document["context_id"],
        root_state_id=document["root_state_id"],
        catalogues=catalogues,
        destinations=destinations,
        rows=rows,
        concretizer_entries=concretizers,
    )
    if not _same_document(model.to_document(), document):
        _fail("final quotient model differs from complete literal replay")
    return model


def _rebuild_threshold(document: dict[str, Any]) -> robust.RobustThresholdProfileV1:
    threshold = robust.RobustThresholdProfileV1(
        document["context_id"],
        document["risk_tolerance"],
        document["reward_ceiling"],
        document["normalized_regret_tolerance"],
    )
    if not _same_document(threshold.to_document(), document):
        _fail("threshold differs from literal replay")
    return threshold


def _verify_source(source: dict[str, Any], solved_audit: robust.RobustPlanAuditV1) -> None:
    _verify_domain_document(
        source,
        domain=CONSTRUCTION_K7_HELDOUT_RECERTIFICATION_RESULT_V1_DOMAIN,
        identity_key="result_id",
        nested_keys={"preregistration", "checkpoint", "transactions"},
        expected_keys=_SOURCE_KEYS,
        label="source result",
    )
    prereg = _mapping(source["preregistration"], "source preregistration")
    _verify_domain_document(
        prereg,
        domain=CONSTRUCTION_K7_HELDOUT_CHECKPOINT_PREREGISTRATION_V1_DOMAIN,
        identity_key="preregistration_id",
        expected_keys=_PREREG_KEYS,
        label="source preregistration",
    )
    checkpoint = _mapping(source["checkpoint"], "source checkpoint")
    _verify_domain_document(
        checkpoint,
        domain=CONSTRUCTION_K7_HELDOUT_COORDINATE_CHECKPOINT_V1_DOMAIN,
        identity_key="checkpoint_id",
        expected_keys=_CHECKPOINT_KEYS,
        label="source coordinate checkpoint",
    )
    transactions = _list(source["transactions"], "source transactions")
    if len(transactions) != 2:
        _fail("source must contain exactly two checkpoint transactions")
    evidence_ids: list[str] = []
    request_ids: list[str] = []
    delta_ids: list[str] = []
    overlay_ids: list[str] = []
    statuses: list[str] = []
    changed: list[str] = []
    prior_overlay_id: str | None = None
    final_audit_document: dict[str, Any] | None = None
    for index, raw in enumerate(transactions, start=1):
        transaction = _mapping(raw, "source transaction")
        _exact_keys(transaction, {"evidence", "request", "delta", "overlay"}, "source transaction")
        evidence = _mapping(transaction["evidence"], "causal evidence")
        request = _mapping(transaction["request"], "recovery request")
        delta = _mapping(transaction["delta"], "validation delta")
        overlay = _mapping(transaction["overlay"], "overlay epoch")
        _verify_domain_document(
            evidence, domain=CONSTRUCTION_K7_HELDOUT_CAUSAL_ROW_EVIDENCE_V1_DOMAIN,
            identity_key="evidence_id", expected_keys=_EVIDENCE_KEYS,
            label="causal evidence",
        )
        _verify_domain_document(
            request, domain=CONSTRUCTION_K7_HELDOUT_RECOVERY_REQUEST_V1_DOMAIN,
            identity_key="request_id", expected_keys=_REQUEST_KEYS,
            label="recovery request",
        )
        _verify_domain_document(
            delta, domain=CONSTRUCTION_K7_HELDOUT_VALIDATION_DELTA_V1_DOMAIN,
            identity_key="delta_id", expected_keys=_DELTA_KEYS,
            label="validation delta",
        )
        _verify_domain_document(
            overlay, domain=CONSTRUCTION_K7_HELDOUT_OVERLAY_EPOCH_V1_DOMAIN,
            identity_key="overlay_id", nested_keys={"delta", "audit"},
            expected_keys=_OVERLAY_KEYS, label="overlay epoch",
        )
        if (
            evidence["transaction_index"] != index
            or request["transaction_index"] != index
            or overlay["transaction_index"] != index
            or request["causal_evidence_id"] != evidence["evidence_id"]
            or delta["request_id"] != request["request_id"]
            or overlay["delta_id"] != delta["delta_id"]
            or overlay["delta"] != delta
            or overlay["prior_overlay_id"] != prior_overlay_id
            or request["request_frozen_before_new_observation"] is not True
            or delta["request_frozen_before_new_observation"] is not True
            or delta["predecessor_is_exact_prefix"] is not True
            or delta["incremental_observer_draws"] != 2_048
            or overlay["ground_solver_invocations"] != 0
            or overlay["evaluation_exact_kernel_calls"] != 0
        ):
            _fail("source transaction chronology or zero-ground overlay claim changed")
        evidence_ids.append(evidence["evidence_id"])
        request_ids.append(request["request_id"])
        delta_ids.append(delta["delta_id"])
        overlay_ids.append(overlay["overlay_id"])
        statuses.append(overlay["audit_status"])
        changed.append(evidence["selected_row_binding_id"])
        prior_overlay_id = overlay["overlay_id"]
        final_audit_document = _mapping(overlay["audit"], "overlay audit")
    assert final_audit_document is not None
    if (
        source["transaction_evidence_ids"] != evidence_ids
        or source["recovery_request_ids"] != request_ids
        or source["validation_delta_ids"] != delta_ids
        or source["overlay_ids"] != overlay_ids
        or source["overlay_audit_statuses"] != statuses
        or statuses != ["FAILED_PROOF_FRONTIER", "CERTIFIED"]
        or source["final_overlay_id"] != overlay_ids[-1]
        or source["final_audit_id"] != solved_audit.audit_id
        or not _same_document(final_audit_document, solved_audit.to_document())
        or source["changed_row_binding_ids"] != sorted(changed)
        or source["changed_row_count"] != 2
        or source["preserved_row_count"] != 6
        or source["incremental_local_ground_draw_count"] != 4_096
        or source["full_4096_row_closure_built"] is not False
        or source["rows_retained_at_base_checkpoint"] != 6
        or source["multi_step_plan_formed_in_abstract_model"] is not True
        or source["local_ground_restoration_only_after_certificate_failure"] is not True
        or source["query_neutral_overlay_reusable"] is not True
        or source["evaluation_exact_kernel_calls"] != 0
        or source["ground_solver_invocations"] != 0
        or source["formal_exact_iid_plan_certificate"] is not False
        or source["official_execution_allowed"] is not False
    ):
        _fail("source recovery chain or final certified audit changed")


@dataclass(frozen=True, slots=True)
class HeldoutOverlayAbstractReuseIndependentVerificationV1:
    result_id: str
    source_result_id: str
    query_id: str
    plan_id: str
    model_id: str
    audit_id: str
    verification_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "verified result"),
            (self.source_result_id, "verified source"),
            (self.query_id, "verified query"),
            (self.plan_id, "verified plan"),
            (self.model_id, "verified model"),
            (self.audit_id, "verified audit"),
            (self.verification_id, "verification"),
        ):
            _cid(value, label)

    def to_document(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_abstract_reuse_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": self.result_id,
            "source_result_id": self.source_result_id,
            "query_id": self.query_id,
            "plan_id": self.plan_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "new_ground_draw_count": 0,
            "observer_call_count": 0,
            "ground_solver_invocations": 0,
            "evaluation_exact_kernel_calls": 0,
            "producer_import_count": 0,
            "independent_literal_model_rebuild": True,
            "independent_quotient_audit_replay": True,
            "valid": True,
            "verification_id": self.verification_id,
        }


def verify_heldout_overlay_abstract_reuse_bytes_v1(
    canonical_result_bytes: bytes,
) -> HeldoutOverlayAbstractReuseIndependentVerificationV1:
    """Verify one complete fresh-reuse document using only canonical bytes."""

    try:
        document = _mapping(
            loads_canonical_json(canonical_result_bytes), "fresh reuse result"
        )
        _verify_domain_document(
            document,
            domain=CONSTRUCTION_K7_HELDOUT_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
            identity_key="result_id",
            nested_keys={"source_result", "query", "plan", "final_quotient_model", "threshold"},
            expected_keys=_RESULT_KEYS,
            label="fresh reuse result",
        )
        model_document = _mapping(document["final_quotient_model"], "final quotient model")
        threshold_document = _mapping(document["threshold"], "threshold")
        model = _rebuild_model(model_document)
        threshold = _rebuild_threshold(threshold_document)
        solved = robust.solve_quotient_robust_h2_v1(model, threshold)
        robust.verify_robust_plan_audit_v1(model, threshold, solved)
        if not solved.certified:
            _fail("independently rebuilt quotient model is not certified")
        source = _mapping(document["source_result"], "source result")
        _verify_source(source, solved)
        query = _mapping(document["query"], "fresh query")
        plan = _mapping(document["plan"], "fresh plan")
        _verify_domain_document(
            query, domain=CONSTRUCTION_K7_HELDOUT_OVERLAY_QUERY_V1_DOMAIN,
            identity_key="query_id", expected_keys=_QUERY_KEYS, label="fresh query",
        )
        _verify_domain_document(
            plan, domain=CONSTRUCTION_K7_HELDOUT_ABSTRACT_PLAN_V1_DOMAIN,
            identity_key="plan_id", nested_keys={"audit"},
            expected_keys=_PLAN_KEYS, label="fresh plan",
        )
        if (
            document["source_result_id"] != source["result_id"]
            or document["source_overlay_id"] != source["final_overlay_id"]
            or document["source_final_audit_id"] != solved.audit_id
            or document["query_id"] != query["query_id"]
            or document["plan_id"] != plan["plan_id"]
            or document["replanned_audit_id"] != solved.audit_id
            or query["source_result_id"] != source["result_id"]
            or query["source_overlay_id"] != source["final_overlay_id"]
            or query["context_id"] != model.context_id
            or query["quotient_model_id"] != model.model_id
            or query["threshold_profile_id"] != threshold.threshold_profile_id
            or query["query_frozen_before_planner_invocation"] is not True
            or query["observer_or_ground_input_present"] is not False
            or query["exact_evaluation_input_present"] is not False
            or plan["query_id"] != query["query_id"]
            or plan["source_audit_id"] != solved.audit_id
            or plan["replanned_audit_id"] != solved.audit_id
            or not _same_document(plan["audit"], solved.to_document())
            or plan["audit_status"] != "CERTIFIED"
            or plan["abstract_planner_invocations"] != 1
            or plan["model_build_invocations"] != 0
            or plan["new_ground_draw_count"] != 0
            or plan["observer_call_count"] != 0
            or plan["ground_solver_invocations"] != 0
            or plan["evaluation_exact_kernel_calls"] != 0
            or document["fresh_occurrence_new_ground_draw_count"] != 0
            or document["fresh_occurrence_observer_call_count"] != 0
            or document["fresh_occurrence_ground_solver_invocations"] != 0
            or document["fresh_occurrence_evaluation_exact_kernel_calls"] != 0
            or document["fresh_occurrence_abstract_planner_invocations"] != 1
            or document["fresh_occurrence_directly_abstract_certified"] is not True
            or document["certificate_failure_triggered_local_recovery"] is not False
            or document["source_local_recovery_reused_as_query_neutral_overlay"] is not True
            or document["formal_exact_iid_plan_certificate"] is not False
            or document["official_execution_allowed"] is not False
            or document["scientific_endpoint_credit_allowed"] is not False
            or document["official_scalar_cost"] is not None
            or document["official_N_break_even"] is not None
            or document["counter_completeness_gate_status"] != "NOT_RUN"
            or document["workload_economics_gate_status"] != "NOT_RUN"
        ):
            _fail("fresh query/plan/result identity or claim lock changed")
        verification_payload = {
            "schema": "acfqp.construction_k7_heldout_abstract_reuse_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": document["result_id"],
            "source_result_id": source["result_id"],
            "query_id": query["query_id"],
            "plan_id": plan["plan_id"],
            "model_id": model.model_id,
            "audit_id": solved.audit_id,
            "new_ground_draw_count": 0,
            "observer_call_count": 0,
            "ground_solver_invocations": 0,
            "evaluation_exact_kernel_calls": 0,
            "producer_import_count": 0,
            "independent_literal_model_rebuild": True,
            "independent_quotient_audit_replay": True,
            "valid": True,
        }
        verification_id = content_id(VERIFICATION_DOMAIN, verification_payload)
        return HeldoutOverlayAbstractReuseIndependentVerificationV1(
            document["result_id"], source["result_id"], query["query_id"],
            plan["plan_id"], model.model_id, solved.audit_id, verification_id,
        )
    except ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error:
        raise
    except Exception as error:
        raise ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error(
            "held-out abstract-reuse bytes failed independent replay"
        ) from error


__all__ = [
    "ConstructionK7HeldoutOverlayAbstractReuseIndependentVerifierV1Error",
    "HeldoutOverlayAbstractReuseIndependentVerificationV1",
    "VERIFICATION_DOMAIN",
    "verify_heldout_overlay_abstract_reuse_bytes_v1",
]
