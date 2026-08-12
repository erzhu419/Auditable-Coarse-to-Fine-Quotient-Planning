"""Producer-free replay of a fresh query on the recovered K6 world model.

The verifier consumes canonical bytes, delegates the embedded recovery result
to the producer-free K6 checkpoint verifier, independently rebuilds the final
interval model and threshold, reruns the H=2 quotient planner, and verifies the
fresh query, plan, result identities, and all zero-ground claim locks.  It
imports neither construction producer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, NoReturn

from acfqp import (
    construction_k7_heldout_k6_checkpoint_recertification_independent_verifier_v1
    as source_verifier,
)
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_PLAN_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_QUERY_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.130"
PROFILE_KEY = (
    "construction_k7_heldout_k6_overlay_abstract_reuse_"
    "independent_verifier_v1"
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_INDEPENDENT_VERIFICATION_V1_DOMAIN
)

_PRODUCER_CONTRACT_VERSION = "2.0.129"
_PRODUCER_PROFILE_KEY = "construction_k7_heldout_k6_overlay_abstract_reuse_v1"


class ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error(
    ValueError
):
    """Canonical bytes, artifact links, or independent K6 replay failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error(
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
        raise ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        _fail(f"{label} fields changed")


def _same(left: Any, right: Any) -> bool:
    return canonical_json_bytes(left) == canonical_json_bytes(right)


def _verify_domain(
    document: dict[str, Any],
    *,
    domain: str,
    identity_key: str,
    expected_keys: set[str],
    nested_keys: set[str] = frozenset(),
    label: str,
) -> dict[str, Any]:
    _exact_keys(document, expected_keys, label)
    identity = _cid(document[identity_key], f"{label} ID")
    payload = {
        key: value
        for key, value in document.items()
        if key != identity_key and key not in nested_keys
    }
    if content_id(domain, payload) != identity:
        _fail(f"{label} content ID changed")
    return payload


_QUERY_PAYLOAD_KEYS = {
    "schema",
    "schema_version",
    "contract_version",
    "profile_key",
    "logical_occurrence_id",
    "occurrence_ordinal",
    "source_result_id",
    "source_overlay_id",
    "context_id",
    "quotient_model_id",
    "threshold_profile_id",
    "horizon",
    "query_frozen_before_planner_invocation",
    "observer_or_ground_input_present",
    "exact_evaluation_input_present",
    "model_construction_input_present",
}
_QUERY_KEYS = _QUERY_PAYLOAD_KEYS | {"query_id"}

_PLAN_PAYLOAD_KEYS = {
    "schema",
    "schema_version",
    "contract_version",
    "profile_key",
    "query_id",
    "source_audit_id",
    "replanned_audit_id",
    "quotient_model_id",
    "threshold_profile_id",
    "audit_status",
    "fresh_query_identity_outside_model_proof",
    "abstract_planner_invocations",
    "model_build_invocations",
    "new_ground_draw_count",
    "observer_call_count",
    "ground_solver_invocations",
    "evaluation_exact_kernel_calls",
    "multi_step_plan_formed_in_abstract_model",
}
_PLAN_KEYS = _PLAN_PAYLOAD_KEYS | {"audit", "plan_id"}

_RESULT_PAYLOAD_KEYS = {
    "schema",
    "schema_version",
    "contract_version",
    "profile_key",
    "source_result_id",
    "source_overlay_id",
    "source_final_audit_id",
    "query_id",
    "plan_id",
    "replanned_audit_id",
    "fresh_occurrence_new_ground_draw_count",
    "fresh_occurrence_observer_call_count",
    "fresh_occurrence_model_build_invocations",
    "fresh_occurrence_ground_solver_invocations",
    "fresh_occurrence_evaluation_exact_kernel_calls",
    "fresh_occurrence_abstract_planner_invocations",
    "fresh_occurrence_directly_abstract_certified",
    "certificate_failure_triggered_local_recovery",
    "source_local_recovery_reused_as_query_neutral_overlay",
    "source_target_vertex_count",
    "construction_certificate_status",
    "formal_exact_iid_plan_certificate",
    "broad_cross_domain_generalization_claimed",
    "official_execution_allowed",
    "scientific_endpoint_credit_allowed",
    "official_scalar_cost",
    "official_N_break_even",
    "counter_completeness_gate_status",
    "workload_economics_gate_status",
}
_RESULT_KEYS = _RESULT_PAYLOAD_KEYS | {
    "source_result",
    "query",
    "plan",
    "final_quotient_model",
    "threshold",
    "result_id",
}


def _rebuild_model(
    document: dict[str, Any],
) -> robust.PartialSupportIntervalModelV1:
    catalogues: list[robust.StateActionCatalogueV1] = []
    for raw in _list(document.get("catalogues"), "model catalogues"):
        item = _mapping(raw, "model catalogue")
        actions: list[robust.CatalogueActionV1] = []
        for raw_action in _list(item.get("actions"), "catalogue actions"):
            action = _mapping(raw_action, "catalogue action")
            rebuilt_action = robust.CatalogueActionV1(
                action["action_id"], action["action_coordinate_key"]
            )
            if not _same(rebuilt_action.to_document(), action):
                _fail("catalogue action differs from literal replay")
            actions.append(rebuilt_action)
        rebuilt = robust.StateActionCatalogueV1(
            item["state_id"], item["state_coordinate_key"], tuple(actions)
        )
        if not _same(rebuilt.to_document(), item):
            _fail("state-action catalogue differs from literal replay")
        catalogues.append(rebuilt)

    destinations: list[robust.RegisteredDestinationV1] = []
    for raw in _list(document.get("destinations"), "model destinations"):
        item = _mapping(raw, "model destination")
        rebuilt = robust.RegisteredDestinationV1(
            item["destination_id"],
            robust.DestinationCategory(item["category"]),
            item["state_id"],
        )
        if not _same(rebuilt.to_document(), item):
            _fail("destination differs from literal replay")
        destinations.append(rebuilt)

    rows: list[robust.IntervalSimplexRowV1] = []
    for raw in _list(document.get("rows"), "model rows"):
        item = _mapping(raw, "model row")
        masses: list[robust.IntervalDestinationMassV1] = []
        for raw_mass in _list(item.get("masses"), "row masses"):
            mass = _mapping(raw_mass, "row mass")
            rebuilt_mass = robust.IntervalDestinationMassV1(
                mass["destination_id"], mass["lower"], mass["upper"]
            )
            if not _same(rebuilt_mass.to_document(), mass):
                _fail("interval mass differs from literal replay")
            masses.append(rebuilt_mass)
        rebuilt = robust.IntervalSimplexRowV1(
            item["state_id"],
            item["remaining_horizon"],
            item["action_id"],
            item["reward_lower"],
            item["reward_upper"],
            item["other_destination_id"],
            tuple(masses),
        )
        if not _same(rebuilt.to_document(), item):
            _fail("interval row differs from literal replay")
        rows.append(rebuilt)

    concretizers: list[robust.DistinctActionConcretizerEntryV1] = []
    for raw in _list(document.get("concretizer_entries"), "model concretizers"):
        item = _mapping(raw, "model concretizer")
        rebuilt = robust.DistinctActionConcretizerEntryV1(
            item["state_coordinate_key"],
            item["state_id"],
            item["abstract_action_key"],
            tuple(item["ground_action_ids"]),
        )
        if not _same(rebuilt.to_document(), item):
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
    if not _same(model.to_document(), document):
        _fail("K6 quotient model differs from complete literal replay")
    return model


def _rebuild_threshold(
    document: dict[str, Any],
) -> robust.RobustThresholdProfileV1:
    threshold = robust.RobustThresholdProfileV1(
        document["context_id"],
        document["risk_tolerance"],
        document["reward_ceiling"],
        document["normalized_regret_tolerance"],
    )
    if not _same(threshold.to_document(), document):
        _fail("K6 threshold differs from literal replay")
    return threshold


@dataclass(frozen=True, slots=True)
class HeldoutK6OverlayAbstractReuseIndependentVerificationV1:
    result_id: str
    source_result_id: str
    source_verification_id: str
    query_id: str
    plan_id: str
    model_id: str
    audit_id: str
    verification_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "verified K6 reuse result"),
            (self.source_result_id, "verified K6 source result"),
            (self.source_verification_id, "source independent verification"),
            (self.query_id, "verified fresh query"),
            (self.plan_id, "verified abstract plan"),
            (self.model_id, "verified K6 model"),
            (self.audit_id, "verified K6 audit"),
            (self.verification_id, "K6 reuse verification"),
        ):
            _cid(value, label)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_k6_abstract_reuse_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": self.result_id,
            "source_result_id": self.source_result_id,
            "source_verification_id": self.source_verification_id,
            "query_id": self.query_id,
            "plan_id": self.plan_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "producer_import_count": 0,
            "source_recovery_independently_replayed": True,
            "independent_literal_model_rebuild": True,
            "independent_fresh_query_identity_replay": True,
            "independent_quotient_audit_replay": True,
            "new_ground_draw_count": 0,
            "observer_call_count": 0,
            "model_build_invocations_in_fresh_occurrence": 0,
            "ground_solver_invocations": 0,
            "evaluation_exact_kernel_calls": 0,
            "valid": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_heldout_k6_overlay_abstract_reuse_bytes_v1(
    canonical_result_bytes: bytes,
) -> HeldoutK6OverlayAbstractReuseIndependentVerificationV1:
    """Verify one fresh K6 abstract reuse result from canonical bytes only."""

    try:
        document = _mapping(
            loads_canonical_json(canonical_result_bytes), "K6 reuse result"
        )
        if canonical_json_bytes(document) != canonical_result_bytes:
            _fail("K6 reuse result bytes are not canonical")
        _verify_domain(
            document,
            domain=CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_REUSE_RESULT_V1_DOMAIN,
            identity_key="result_id",
            expected_keys=_RESULT_KEYS,
            nested_keys={
                "source_result",
                "query",
                "plan",
                "final_quotient_model",
                "threshold",
            },
            label="K6 reuse result",
        )

        source = _mapping(document["source_result"], "K6 source result")
        source_verification = (
            source_verifier.verify_heldout_k6_checkpoint_recertification_bytes_v1(
                canonical_json_bytes(source)
            )
        )
        query = _mapping(document["query"], "fresh K6 query")
        plan = _mapping(document["plan"], "fresh K6 plan")
        model_document = _mapping(
            document["final_quotient_model"], "fresh K6 quotient model"
        )
        threshold_document = _mapping(document["threshold"], "K6 threshold")
        _verify_domain(
            query,
            domain=CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_QUERY_V1_DOMAIN,
            identity_key="query_id",
            expected_keys=_QUERY_KEYS,
            label="fresh K6 query",
        )
        _verify_domain(
            plan,
            domain=CONSTRUCTION_K7_HELDOUT_K6_ABSTRACT_PLAN_V1_DOMAIN,
            identity_key="plan_id",
            expected_keys=_PLAN_KEYS,
            nested_keys={"audit"},
            label="fresh K6 plan",
        )

        source_overlay = _mapping(source["overlay"], "K6 source overlay")
        source_model = _mapping(
            source_overlay["final_quotient_model"], "K6 source final model"
        )
        source_threshold = _mapping(source["threshold"], "K6 source threshold")
        model = _rebuild_model(model_document)
        threshold = _rebuild_threshold(threshold_document)
        audit = robust.solve_quotient_robust_h2_v1(model, threshold)
        if audit.status is not robust.RobustAuditStatus.CERTIFIED:
            _fail("fresh K6 quotient replay did not certify")
        audit_document = _mapping(plan["audit"], "fresh K6 audit")

        if (
            not _same(model_document, source_model)
            or not _same(threshold_document, source_threshold)
            or source_verification.result_id != source["result_id"]
            or source_verification.final_model_id != model.model_id
            or source_verification.final_audit_id != audit.audit_id
            or query["schema"]
            != "acfqp.construction_k7_heldout_k6_overlay_query.v1"
            or query["schema_version"] != "1.0.0"
            or query["contract_version"] != _PRODUCER_CONTRACT_VERSION
            or query["profile_key"] != _PRODUCER_PROFILE_KEY
            or type(query["occurrence_ordinal"]) is not int
            or query["occurrence_ordinal"] <= 0
            or query["logical_occurrence_id"]
            in {source["result_id"], source_overlay["overlay_id"]}
            or query["source_result_id"] != source["result_id"]
            or query["source_overlay_id"] != source_overlay["overlay_id"]
            or query["context_id"] != model.context_id
            or query["quotient_model_id"] != model.model_id
            or query["threshold_profile_id"] != threshold.threshold_profile_id
            or query["horizon"] != 2
            or query["query_frozen_before_planner_invocation"] is not True
            or query["observer_or_ground_input_present"] is not False
            or query["exact_evaluation_input_present"] is not False
            or query["model_construction_input_present"] is not False
        ):
            _fail("fresh K6 query or source-world-model binding changed")

        if (
            plan["schema"]
            != "acfqp.construction_k7_heldout_k6_abstract_plan.v1"
            or plan["schema_version"] != "1.0.0"
            or plan["contract_version"] != _PRODUCER_CONTRACT_VERSION
            or plan["profile_key"] != _PRODUCER_PROFILE_KEY
            or plan["query_id"] != query["query_id"]
            or plan["source_audit_id"] != source_overlay["audit_id"]
            or plan["replanned_audit_id"] != audit.audit_id
            or plan["quotient_model_id"] != model.model_id
            or plan["threshold_profile_id"] != threshold.threshold_profile_id
            or plan["audit_status"] != "CERTIFIED"
            or not _same(audit_document, audit.to_document())
            or plan["fresh_query_identity_outside_model_proof"] is not True
            or plan["abstract_planner_invocations"] != 1
            or plan["model_build_invocations"] != 0
            or plan["new_ground_draw_count"] != 0
            or plan["observer_call_count"] != 0
            or plan["ground_solver_invocations"] != 0
            or plan["evaluation_exact_kernel_calls"] != 0
            or plan["multi_step_plan_formed_in_abstract_model"] is not True
        ):
            _fail("fresh K6 abstract plan or numerical audit changed")

        if (
            document["schema"]
            != "acfqp.construction_k7_heldout_k6_abstract_reuse_result.v1"
            or document["schema_version"] != "1.0.0"
            or document["contract_version"] != _PRODUCER_CONTRACT_VERSION
            or document["profile_key"] != _PRODUCER_PROFILE_KEY
            or document["source_result_id"] != source["result_id"]
            or document["source_overlay_id"] != source_overlay["overlay_id"]
            or document["source_final_audit_id"] != source_overlay["audit_id"]
            or document["query_id"] != query["query_id"]
            or document["plan_id"] != plan["plan_id"]
            or document["replanned_audit_id"] != audit.audit_id
            or document["fresh_occurrence_new_ground_draw_count"] != 0
            or document["fresh_occurrence_observer_call_count"] != 0
            or document["fresh_occurrence_model_build_invocations"] != 0
            or document["fresh_occurrence_ground_solver_invocations"] != 0
            or document["fresh_occurrence_evaluation_exact_kernel_calls"] != 0
            or document["fresh_occurrence_abstract_planner_invocations"] != 1
            or document["fresh_occurrence_directly_abstract_certified"] is not True
            or document["certificate_failure_triggered_local_recovery"] is not False
            or document["source_local_recovery_reused_as_query_neutral_overlay"]
            is not True
            or document["source_target_vertex_count"] != 6
            or document["construction_certificate_status"]
            != "CONDITIONAL_STATISTICAL_ABSTRACT_PLAN_CERTIFIED"
            or document["formal_exact_iid_plan_certificate"] is not False
            or document["broad_cross_domain_generalization_claimed"] is not False
            or document["official_execution_allowed"] is not False
            or document["scientific_endpoint_credit_allowed"] is not False
            or document["official_scalar_cost"] is not None
            or document["official_N_break_even"] is not None
            or document["counter_completeness_gate_status"] != "NOT_RUN"
            or document["workload_economics_gate_status"] != "NOT_RUN"
        ):
            _fail("fresh K6 reuse result identity or claim locks changed")

        payload = {
            "schema": "acfqp.construction_k7_heldout_k6_abstract_reuse_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": document["result_id"],
            "source_result_id": source["result_id"],
            "source_verification_id": source_verification.verification_id,
            "query_id": query["query_id"],
            "plan_id": plan["plan_id"],
            "model_id": model.model_id,
            "audit_id": audit.audit_id,
            "producer_import_count": 0,
            "source_recovery_independently_replayed": True,
            "independent_literal_model_rebuild": True,
            "independent_fresh_query_identity_replay": True,
            "independent_quotient_audit_replay": True,
            "new_ground_draw_count": 0,
            "observer_call_count": 0,
            "model_build_invocations_in_fresh_occurrence": 0,
            "ground_solver_invocations": 0,
            "evaluation_exact_kernel_calls": 0,
            "valid": True,
        }
        return HeldoutK6OverlayAbstractReuseIndependentVerificationV1(
            document["result_id"],
            source["result_id"],
            source_verification.verification_id,
            query["query_id"],
            plan["plan_id"],
            model.model_id,
            audit.audit_id,
            content_id(VERIFICATION_DOMAIN, payload),
        )
    except ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error:
        raise
    except Exception as error:
        raise ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error(
            "K6 abstract-reuse bytes failed independent replay"
        ) from error


__all__ = [
    "ConstructionK7HeldoutK6OverlayAbstractReuseIndependentVerifierV1Error",
    "HeldoutK6OverlayAbstractReuseIndependentVerificationV1",
    "VERIFICATION_DOMAIN",
    "verify_heldout_k6_overlay_abstract_reuse_bytes_v1",
]
