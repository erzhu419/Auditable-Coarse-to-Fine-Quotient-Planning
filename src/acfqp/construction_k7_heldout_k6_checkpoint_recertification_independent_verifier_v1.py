"""Producer-free canonical replay of the K6 checkpoint recovery.

The verifier imports no K6 checkpoint producer.  It reconstructs the public
K6 context, frozen relational profile, threshold, base and final interval
models from literal canonical bytes.  It reruns the failed base H=2 audit,
all twenty zero-OTHER causal counterfactuals, and the final certified audit,
then recomputes every construction-domain identity and claim lock.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, NoReturn

from acfqp import observation_support_relational_adapter_v1 as relational
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import transition_tuple_observer_v1 as observer
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_K6_CAUSAL_ROW_EVIDENCE_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_CHECKPOINT_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_COORDINATE_CHECKPOINT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_K6_VALIDATION_DELTA_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.128"
PROFILE_KEY = (
    "construction_k7_heldout_k6_checkpoint_recertification_"
    "independent_verifier_v1"
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_INDEPENDENT_VERIFICATION_V1_DOMAIN
)

_PRODUCER_CONTRACT_VERSION = "2.0.127"
_PRODUCER_PROFILE_KEY = "construction_k7_heldout_k6_checkpoint_recertification_v1"
_BASE_CHECKPOINT = 8_192
_RECOVERY_CHECKPOINT = 16_384
_ROW_COUNT = 20
_COORDINATE_COUNT = 10
_COORDINATE_SELECTION_RULE = (
    "MAX_CURRENT_MINIMUM_SLACK_THEN_LOWEST_REGISTERED_ORDINAL"
)
_CAUSAL_SELECTION_RULE = (
    "MAX_ZERO_OTHER_MINIMUM_SLACK_THEN_HIGHEST_HORIZON_"
    "THEN_PLANNER_ROW_ID"
)


class ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error(ValueError):
    """Canonical bytes, numerical replay, or K6 identity chain failed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error(message)


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
        raise ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error(
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


_PREREG_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "target_context_key", "target_context_id", "target_topology_id",
    "source_skeleton_id", "source_observation_log_id", "source_vertex_counts",
    "target_vertex_count", "validation_checkpoints", "max_local_transactions",
    "coordinate_selection_rule", "causal_selection_rule",
    "request_must_precede_new_observation", "full_target_closure_authorized",
    "evaluation_exact_kernel_authorized", "ground_solver_authorized",
    "preregistration_id",
}
_CHECKPOINT_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "preregistration_id", "closure_id", "base_bridge_id", "base_audit_id",
    "base_audit_status", "refinement_result_id", "refinement_outcome",
    "candidate_spec_ids", "candidate_profile_ids", "candidate_audit_ids",
    "candidate_minimum_slacks", "selected_ordinal", "selected_spec_id",
    "selected_profile_id", "selection_rule",
    "selected_using_future_checkpoint_data",
    "observer_draws_during_coordinate_selection", "checkpoint_id",
}
_CAUSAL_CANDIDATE_KEYS = {
    "planner_row_id", "partial_row_id", "row_binding_id",
    "remaining_horizon", "zero_other_model_id", "zero_other_audit_id",
    "root_reward_lower", "root_failure_upper", "normalized_regret_upper",
    "minimum_certificate_slack", "certified",
}
_EVIDENCE_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "checkpoint_id", "failed_model_id", "failed_audit_id",
    "failed_frontier_id", "selected_assignment_ids", "candidates",
    "selected_planner_row_id", "selected_partial_row_id",
    "selected_row_binding_id", "selected_remaining_horizon",
    "selected_minimum_certificate_slack", "selection_rule",
    "counterfactual_scope", "counterfactual_observer_draws",
    "future_checkpoint_data_accesses", "minimum_authorized_cardinality",
    "zero_row_baseline_failed", "global_candidate_uniqueness_claimed",
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
    "schema", "schema_version", "contract_version", "profile_key",
    "request_id", "row_binding_id", "before_partial_row_id",
    "after_partial_row_id", "before_confidence_authority_id",
    "after_confidence_authority_id", "before_validation_checkpoint",
    "after_validation_checkpoint", "incremental_observer_draws",
    "incremental_random_word_calls", "incremental_rejections",
    "before_observation_prefix_digest", "after_observation_prefix_digest",
    "predecessor_is_exact_prefix", "request_frozen_before_new_observation",
    "delta_id",
}
_OVERLAY_PAYLOAD_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "transaction_index", "prior_bridge_id", "prior_model_id",
    "prior_audit_id", "delta_id", "changed_row_binding_ids",
    "preserved_row_binding_ids", "bridge_id", "quotient_model_id",
    "audit_id", "audit_status", "root_failure_upper",
    "normalized_regret_upper", "immutable_query_neutral_overlay",
    "abstract_planner_invocations", "ground_solver_invocations",
    "evaluation_exact_kernel_calls",
}
_OVERLAY_KEYS = _OVERLAY_PAYLOAD_KEYS | {
    "delta", "final_quotient_model", "audit", "overlay_id"
}
_RESULT_PAYLOAD_KEYS = {
    "schema", "schema_version", "contract_version", "profile_key",
    "preregistration_id", "checkpoint_id", "causal_evidence_id",
    "recovery_request_id", "validation_delta_id", "final_overlay_id",
    "target_context_id", "source_vertex_counts", "target_vertex_count",
    "base_bridge_id", "base_quotient_model_id", "base_audit_id",
    "base_audit_status", "final_bridge_id", "final_quotient_model_id",
    "final_audit_id", "final_audit_status", "final_root_failure_upper",
    "final_normalized_regret_upper", "base_observer_draw_count",
    "incremental_local_ground_draw_count", "changed_row_binding_ids",
    "preserved_row_binding_ids", "changed_row_count", "preserved_row_count",
    "minimum_recovery_cardinality_within_registered_screen",
    "global_row_choice_uniqueness_claimed", "full_16384_row_closure_built",
    "rows_retained_at_base_checkpoint", "multi_step_plan_formed_in_abstract_model",
    "local_ground_restoration_only_after_certificate_failure",
    "query_neutral_overlay_reusable", "coordinate_candidates_observation_driven",
    "coordinate_primitive_invention_count", "evaluation_exact_kernel_calls",
    "ground_solver_invocations", "construction_certificate_status",
    "formal_exact_iid_plan_certificate", "heldout_family_scope",
    "broad_cross_domain_generalization_claimed", "official_execution_allowed",
    "scientific_endpoint_credit_allowed", "official_scalar_cost",
    "official_N_break_even", "counter_completeness_gate_status",
    "workload_economics_gate_status",
}
_RESULT_KEYS = _RESULT_PAYLOAD_KEYS | {
    "context", "coordinate_profile", "threshold", "base_quotient_model",
    "preregistration", "checkpoint", "causal_evidence", "request", "delta",
    "overlay", "result_id",
}


def _rebuild_model(document: dict[str, Any]) -> robust.PartialSupportIntervalModelV1:
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
    rebuilt_model = robust.build_partial_support_model_v1(
        context_id=document["context_id"],
        root_state_id=document["root_state_id"],
        catalogues=catalogues,
        destinations=destinations,
        rows=rows,
        concretizer_entries=concretizers,
    )
    if not _same(rebuilt_model.to_document(), document):
        _fail("quotient model differs from complete literal replay")
    return rebuilt_model


def _rebuild_threshold(document: dict[str, Any]) -> robust.RobustThresholdProfileV1:
    threshold = robust.RobustThresholdProfileV1(
        document["context_id"],
        document["risk_tolerance"],
        document["reward_ceiling"],
        document["normalized_regret_tolerance"],
    )
    if not _same(threshold.to_document(), document):
        _fail("threshold differs from literal replay")
    return threshold


def _zero_other_model(
    model: robust.PartialSupportIntervalModelV1,
    planner_row_id: str,
) -> robust.PartialSupportIntervalModelV1:
    found = False
    rows: list[robust.IntervalSimplexRowV1] = []
    for row in model.rows:
        if row.row_id != planner_row_id:
            rows.append(row)
            continue
        found = True
        rows.append(
            robust.IntervalSimplexRowV1(
                row.state_id,
                row.remaining_horizon,
                row.action_id,
                row.reward_lower,
                row.reward_upper,
                row.other_destination_id,
                tuple(
                    robust.IntervalDestinationMassV1(
                        mass.destination_id,
                        (
                            Fraction(0)
                            if mass.destination_id == row.other_destination_id
                            else mass.lower
                        ),
                        (
                            Fraction(0)
                            if mass.destination_id == row.other_destination_id
                            else mass.upper
                        ),
                    )
                    for mass in row.masses
                ),
            )
        )
    if not found:
        _fail("causal evidence references an absent base-model row")
    return robust.build_partial_support_model_v1(
        context_id=model.context_id,
        root_state_id=model.root_state_id,
        catalogues=model.catalogues,
        destinations=model.destinations,
        rows=rows,
        concretizer_entries=model.concretizer_entries,
    )


def _slack(
    audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> Fraction:
    return min(
        threshold.risk_tolerance - audit.root_failure_upper,
        threshold.normalized_regret_tolerance - audit.normalized_regret_upper,
    )


def _replay_causal_candidates(
    evidence: dict[str, Any],
    base_model: robust.PartialSupportIntervalModelV1,
    base_audit: robust.RobustPlanAuditV1,
    threshold: robust.RobustThresholdProfileV1,
) -> list[dict[str, Any]]:
    frontier = base_audit.failed_frontier
    if frontier is None:
        _fail("base audit has no failed frontier")
    raw_candidates = _list(evidence["candidates"], "causal candidates")
    if len(raw_candidates) != _ROW_COUNT:
        _fail("causal screen does not contain exactly twenty rows")
    by_planner: dict[str, dict[str, Any]] = {}
    for raw in raw_candidates:
        candidate = _mapping(raw, "causal candidate")
        _exact_keys(candidate, _CAUSAL_CANDIDATE_KEYS, "causal candidate")
        planner_id = _cid(candidate["planner_row_id"], "candidate planner row")
        if planner_id in by_planner:
            _fail("causal screen duplicates a planner row")
        zero_model = _zero_other_model(base_model, planner_id)
        zero_audit = robust.solve_quotient_robust_h2_v1(zero_model, threshold)
        robust.verify_robust_plan_audit_v1(zero_model, threshold, zero_audit)
        expected = {
            **candidate,
            "zero_other_model_id": zero_model.model_id,
            "zero_other_audit_id": zero_audit.audit_id,
            "root_reward_lower": zero_audit.root_reward_lower,
            "root_failure_upper": zero_audit.root_failure_upper,
            "normalized_regret_upper": zero_audit.normalized_regret_upper,
            "minimum_certificate_slack": _slack(zero_audit, threshold),
            "certified": zero_audit.certified,
        }
        if not _same(candidate, expected):
            _fail("causal counterfactual differs from independent replay")
        model_row = next(
            item for item in base_model.rows if item.row_id == planner_id
        )
        if candidate["remaining_horizon"] != model_row.remaining_horizon:
            _fail("causal candidate horizon differs from the base-model row")
        by_planner[planner_id] = candidate
    if set(by_planner) != set(frontier.other_positive_row_ids):
        _fail("causal screen differs from the complete failed frontier")
    values = list(by_planner.values())
    values.sort(
        key=lambda item: (
            -item["minimum_certificate_slack"],
            -item["remaining_horizon"],
            item["planner_row_id"],
        )
    )
    if not _same(values, raw_candidates):
        _fail("causal candidates are not in the preregistered order")
    return values


@dataclass(frozen=True, slots=True)
class HeldoutK6CheckpointIndependentVerificationV1:
    result_id: str
    base_model_id: str
    base_audit_id: str
    causal_evidence_id: str
    final_model_id: str
    final_audit_id: str
    verification_id: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.result_id, "verified K6 result"),
            (self.base_model_id, "verified base model"),
            (self.base_audit_id, "verified base audit"),
            (self.causal_evidence_id, "verified causal evidence"),
            (self.final_model_id, "verified final model"),
            (self.final_audit_id, "verified final audit"),
            (self.verification_id, "K6 verification"),
        ):
            _cid(value, label)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_heldout_k6_recertification_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": self.result_id,
            "base_model_id": self.base_model_id,
            "base_audit_id": self.base_audit_id,
            "causal_evidence_id": self.causal_evidence_id,
            "final_model_id": self.final_model_id,
            "final_audit_id": self.final_audit_id,
            "validated_coordinate_registry_count": _COORDINATE_COUNT,
            "replayed_causal_candidate_count": _ROW_COUNT,
            "replayed_changed_row_count": 1,
            "replayed_preserved_row_count": _ROW_COUNT - 1,
            "new_observer_draw_count": 0,
            "evaluation_exact_kernel_calls": 0,
            "ground_solver_invocations": 0,
            "producer_import_count": 0,
            "independent_literal_model_rebuild": True,
            "independent_base_failure_replay": True,
            "independent_coordinate_candidate_model_replay": False,
            "independent_causal_counterfactual_replay": True,
            "physical_row_projection_independently_reconstructed": False,
            "independent_final_certificate_replay": True,
            "valid": True,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_heldout_k6_checkpoint_recertification_bytes_v1(
    canonical_result_bytes: bytes,
) -> HeldoutK6CheckpointIndependentVerificationV1:
    """Verify one K6 recovery result from canonical bytes only."""

    try:
        document = _mapping(
            loads_canonical_json(canonical_result_bytes), "K6 result"
        )
        if canonical_json_bytes(document) != canonical_result_bytes:
            _fail("K6 result bytes are not canonical")
        _verify_domain(
            document,
            domain=CONSTRUCTION_K7_HELDOUT_K6_RECERTIFICATION_RESULT_V1_DOMAIN,
            identity_key="result_id",
            expected_keys=_RESULT_KEYS,
            nested_keys={
                "context", "coordinate_profile", "threshold",
                "base_quotient_model", "preregistration", "checkpoint",
                "causal_evidence", "request", "delta", "overlay",
            },
            label="K6 result",
        )
        context_document = _mapping(document["context"], "K6 context")
        context = observer.public_context_by_key_v1("opaque_graph_k6_v0")
        if not _same(context_document, context.to_document()):
            _fail("K6 public context differs from the registered target")
        profile_document = _mapping(
            document["coordinate_profile"], "K6 coordinate profile"
        )
        profile = relational.base_coordinate_profile_v1()
        if not _same(profile_document, profile.to_document()):
            _fail("K6 coordinate profile differs from the frozen base grammar")
        threshold = _rebuild_threshold(_mapping(document["threshold"], "threshold"))
        base_model = _rebuild_model(
            _mapping(document["base_quotient_model"], "base quotient model")
        )
        base_audit = robust.solve_quotient_robust_h2_v1(base_model, threshold)
        robust.verify_robust_plan_audit_v1(base_model, threshold, base_audit)
        if base_audit.status is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER:
            _fail("independently rebuilt K6 base model does not fail")

        prereg = _mapping(document["preregistration"], "K6 preregistration")
        checkpoint = _mapping(document["checkpoint"], "K6 checkpoint")
        evidence = _mapping(document["causal_evidence"], "K6 causal evidence")
        request = _mapping(document["request"], "K6 request")
        delta = _mapping(document["delta"], "K6 delta")
        overlay = _mapping(document["overlay"], "K6 overlay")
        _verify_domain(
            prereg,
            domain=CONSTRUCTION_K7_HELDOUT_K6_CHECKPOINT_PREREGISTRATION_V1_DOMAIN,
            identity_key="preregistration_id",
            expected_keys=_PREREG_KEYS,
            label="K6 preregistration",
        )
        _verify_domain(
            checkpoint,
            domain=CONSTRUCTION_K7_HELDOUT_K6_COORDINATE_CHECKPOINT_V1_DOMAIN,
            identity_key="checkpoint_id",
            expected_keys=_CHECKPOINT_KEYS,
            label="K6 coordinate checkpoint",
        )
        _verify_domain(
            evidence,
            domain=CONSTRUCTION_K7_HELDOUT_K6_CAUSAL_ROW_EVIDENCE_V1_DOMAIN,
            identity_key="evidence_id",
            expected_keys=_EVIDENCE_KEYS,
            label="K6 causal evidence",
        )
        _verify_domain(
            request,
            domain=CONSTRUCTION_K7_HELDOUT_K6_RECOVERY_REQUEST_V1_DOMAIN,
            identity_key="request_id",
            expected_keys=_REQUEST_KEYS,
            label="K6 recovery request",
        )
        _verify_domain(
            delta,
            domain=CONSTRUCTION_K7_HELDOUT_K6_VALIDATION_DELTA_V1_DOMAIN,
            identity_key="delta_id",
            expected_keys=_DELTA_KEYS,
            label="K6 validation delta",
        )
        _verify_domain(
            overlay,
            domain=CONSTRUCTION_K7_HELDOUT_K6_OVERLAY_EPOCH_V1_DOMAIN,
            identity_key="overlay_id",
            expected_keys=_OVERLAY_KEYS,
            nested_keys={"delta", "final_quotient_model", "audit"},
            label="K6 overlay",
        )

        coordinate_slack = _slack(base_audit, threshold)
        if (
            prereg["schema"]
            != "acfqp.construction_k7_heldout_k6_checkpoint_preregistration.v1"
            or prereg["contract_version"] != _PRODUCER_CONTRACT_VERSION
            or prereg["profile_key"] != _PRODUCER_PROFILE_KEY
            or prereg["target_context_key"] != "opaque_graph_k6_v0"
            or prereg["target_context_id"] != context.context_id
            or prereg["target_topology_id"] != context.topology.topology_id
            or prereg["source_vertex_counts"] != [4]
            or prereg["target_vertex_count"] != 6
            or prereg["validation_checkpoints"]
            != [_BASE_CHECKPOINT, _RECOVERY_CHECKPOINT]
            or prereg["max_local_transactions"] != 1
            or prereg["coordinate_selection_rule"] != _COORDINATE_SELECTION_RULE
            or prereg["causal_selection_rule"] != _CAUSAL_SELECTION_RULE
            or prereg["request_must_precede_new_observation"] is not True
            or prereg["full_target_closure_authorized"] is not False
            or prereg["evaluation_exact_kernel_authorized"] is not False
            or prereg["ground_solver_authorized"] is not False
            or checkpoint["preregistration_id"] != prereg["preregistration_id"]
            or checkpoint["base_audit_id"] != base_audit.audit_id
            or checkpoint["base_audit_status"] != "FAILED_PROOF_FRONTIER"
            or checkpoint["refinement_outcome"] != "NO_SOUND_COVER"
            or len(checkpoint["candidate_spec_ids"]) != _COORDINATE_COUNT
            or len(checkpoint["candidate_profile_ids"]) != _COORDINATE_COUNT
            or len(checkpoint["candidate_audit_ids"]) != _COORDINATE_COUNT
            or len(set(checkpoint["candidate_spec_ids"])) != _COORDINATE_COUNT
            or len(set(checkpoint["candidate_profile_ids"])) != _COORDINATE_COUNT
            or checkpoint["candidate_audit_ids"][0] != base_audit.audit_id
            or checkpoint["candidate_minimum_slacks"]
            != [coordinate_slack] * _COORDINATE_COUNT
            or checkpoint["selected_ordinal"] != 0
            or checkpoint["selected_spec_id"] != checkpoint["candidate_spec_ids"][0]
            or checkpoint["selected_profile_id"] != profile.profile_id
            or checkpoint["selected_profile_id"]
            != checkpoint["candidate_profile_ids"][0]
            or checkpoint["selection_rule"] != _COORDINATE_SELECTION_RULE
            or checkpoint["selected_using_future_checkpoint_data"] is not False
            or checkpoint["observer_draws_during_coordinate_selection"] != 0
        ):
            _fail("K6 preregistration or coordinate checkpoint changed")

        causal_candidates = _replay_causal_candidates(
            evidence, base_model, base_audit, threshold
        )
        selected = causal_candidates[0]
        assignment_ids = sorted(
            item.assignment_id for item in base_audit.assignments
        )
        if (
            evidence["checkpoint_id"] != checkpoint["checkpoint_id"]
            or evidence["failed_model_id"] != base_model.model_id
            or evidence["failed_audit_id"] != base_audit.audit_id
            or evidence["failed_frontier_id"]
            != base_audit.failed_frontier.frontier_id
            or evidence["selected_assignment_ids"] != assignment_ids
            or evidence["selected_planner_row_id"] != selected["planner_row_id"]
            or evidence["selected_partial_row_id"] != selected["partial_row_id"]
            or evidence["selected_row_binding_id"] != selected["row_binding_id"]
            or evidence["selected_remaining_horizon"] != 2
            or evidence["selected_minimum_certificate_slack"]
            != selected["minimum_certificate_slack"]
            or selected["certified"] is not True
            or evidence["selection_rule"] != _CAUSAL_SELECTION_RULE
            or evidence["counterfactual_scope"] != "CURRENT_FAILED_MODEL_ONLY"
            or evidence["counterfactual_observer_draws"] != 0
            or evidence["future_checkpoint_data_accesses"] != 0
            or evidence["minimum_authorized_cardinality"] != 1
            or evidence["zero_row_baseline_failed"] is not True
            or evidence["global_candidate_uniqueness_claimed"] is not False
        ):
            _fail("K6 causal evidence identity or selected row changed")

        final_model_document = _mapping(
            overlay["final_quotient_model"], "final quotient model"
        )
        final_model = _rebuild_model(final_model_document)
        final_audit = robust.solve_quotient_robust_h2_v1(final_model, threshold)
        robust.verify_robust_plan_audit_v1(final_model, threshold, final_audit)
        if not final_audit.certified:
            _fail("independently rebuilt K6 overlay does not certify")
        changed = [selected["row_binding_id"]]
        preserved = document["preserved_row_binding_ids"]
        causal_binding_ids = {
            item["row_binding_id"] for item in causal_candidates
        }
        if (
            request["preregistration_id"] != prereg["preregistration_id"]
            or request["causal_evidence_id"] != evidence["evidence_id"]
            or request["row_binding_id"] != selected["row_binding_id"]
            or request["before_partial_row_id"] != selected["partial_row_id"]
            or request["from_validation_checkpoint"] != _BASE_CHECKPOINT
            or request["to_validation_checkpoint"] != _RECOVERY_CHECKPOINT
            or request["authorized_incremental_draws"] != 8_192
            or request["request_frozen_before_new_observation"] is not True
            or request["single_row_only"] is not True
            or delta["request_id"] != request["request_id"]
            or delta["row_binding_id"] != request["row_binding_id"]
            or delta["before_partial_row_id"] != request["before_partial_row_id"]
            or delta["before_validation_checkpoint"] != _BASE_CHECKPOINT
            or delta["after_validation_checkpoint"] != _RECOVERY_CHECKPOINT
            or delta["incremental_observer_draws"] != 8_192
            or delta["incremental_random_word_calls"]
            != 8_192 + delta["incremental_rejections"]
            or delta["predecessor_is_exact_prefix"] is not True
            or delta["request_frozen_before_new_observation"] is not True
            or overlay["transaction_index"] != 1
            or overlay["prior_model_id"] != base_model.model_id
            or overlay["prior_audit_id"] != base_audit.audit_id
            or overlay["delta_id"] != delta["delta_id"]
            or not _same(overlay["delta"], delta)
            or overlay["changed_row_binding_ids"] != changed
            or overlay["preserved_row_binding_ids"] != preserved
            or len(preserved) != _ROW_COUNT - 1
            or selected["row_binding_id"] in preserved
            or len(set(preserved)) != len(preserved)
            or set(preserved) != causal_binding_ids - set(changed)
            or overlay["quotient_model_id"] != final_model.model_id
            or overlay["audit_id"] != final_audit.audit_id
            or overlay["audit_status"] != "CERTIFIED"
            or not _same(overlay["audit"], final_audit.to_document())
            or overlay["root_failure_upper"] != final_audit.root_failure_upper
            or overlay["normalized_regret_upper"]
            != final_audit.normalized_regret_upper
            or overlay["immutable_query_neutral_overlay"] is not True
            or overlay["abstract_planner_invocations"] != 1
            or overlay["ground_solver_invocations"] != 0
            or overlay["evaluation_exact_kernel_calls"] != 0
        ):
            _fail("K6 request/delta/overlay chronology changed")

        if (
            document["preregistration_id"] != prereg["preregistration_id"]
            or document["checkpoint_id"] != checkpoint["checkpoint_id"]
            or document["causal_evidence_id"] != evidence["evidence_id"]
            or document["recovery_request_id"] != request["request_id"]
            or document["validation_delta_id"] != delta["delta_id"]
            or document["final_overlay_id"] != overlay["overlay_id"]
            or document["target_context_id"] != context.context_id
            or document["base_bridge_id"] != checkpoint["base_bridge_id"]
            or overlay["prior_bridge_id"] != checkpoint["base_bridge_id"]
            or document["final_bridge_id"] != overlay["bridge_id"]
            or document["source_vertex_counts"] != [4]
            or document["target_vertex_count"] != 6
            or document["base_quotient_model_id"] != base_model.model_id
            or document["base_audit_id"] != base_audit.audit_id
            or document["base_audit_status"] != "FAILED_PROOF_FRONTIER"
            or document["final_quotient_model_id"] != final_model.model_id
            or document["final_audit_id"] != final_audit.audit_id
            or document["final_audit_status"] != "CERTIFIED"
            or document["final_root_failure_upper"] != final_audit.root_failure_upper
            or document["final_normalized_regret_upper"]
            != final_audit.normalized_regret_upper
            or document["base_observer_draw_count"] != _ROW_COUNT * (64 + 8_192)
            or document["incremental_local_ground_draw_count"] != 8_192
            or document["changed_row_binding_ids"] != changed
            or document["changed_row_count"] != 1
            or document["preserved_row_count"] != _ROW_COUNT - 1
            or document["minimum_recovery_cardinality_within_registered_screen"] != 1
            or document["global_row_choice_uniqueness_claimed"] is not False
            or document["full_16384_row_closure_built"] is not False
            or document["rows_retained_at_base_checkpoint"] != _ROW_COUNT - 1
            or document["multi_step_plan_formed_in_abstract_model"] is not True
            or document["local_ground_restoration_only_after_certificate_failure"]
            is not True
            or document["query_neutral_overlay_reusable"] is not True
            or document["coordinate_candidates_observation_driven"] is not True
            or document["coordinate_primitive_invention_count"] != 0
            or document["evaluation_exact_kernel_calls"] != 0
            or document["ground_solver_invocations"] != 0
            or document["construction_certificate_status"]
            != "CONDITIONAL_STATISTICAL_ABSTRACT_PLAN_CERTIFIED"
            or document["formal_exact_iid_plan_certificate"] is not False
            or document["heldout_family_scope"]
            != "REGISTERED_N4_SOURCE_TO_K6_TARGET_ONLY"
            or document["broad_cross_domain_generalization_claimed"] is not False
            or document["official_execution_allowed"] is not False
            or document["scientific_endpoint_credit_allowed"] is not False
            or document["official_scalar_cost"] is not None
            or document["official_N_break_even"] is not None
            or document["counter_completeness_gate_status"] != "NOT_RUN"
            or document["workload_economics_gate_status"] != "NOT_RUN"
        ):
            _fail("K6 result identity or claim locks changed")

        payload = {
            "schema": "acfqp.construction_k7_heldout_k6_recertification_independent_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": document["result_id"],
            "base_model_id": base_model.model_id,
            "base_audit_id": base_audit.audit_id,
            "causal_evidence_id": evidence["evidence_id"],
            "final_model_id": final_model.model_id,
            "final_audit_id": final_audit.audit_id,
            "validated_coordinate_registry_count": _COORDINATE_COUNT,
            "replayed_causal_candidate_count": _ROW_COUNT,
            "replayed_changed_row_count": 1,
            "replayed_preserved_row_count": _ROW_COUNT - 1,
            "new_observer_draw_count": 0,
            "evaluation_exact_kernel_calls": 0,
            "ground_solver_invocations": 0,
            "producer_import_count": 0,
            "independent_literal_model_rebuild": True,
            "independent_base_failure_replay": True,
            "independent_coordinate_candidate_model_replay": False,
            "independent_causal_counterfactual_replay": True,
            "physical_row_projection_independently_reconstructed": False,
            "independent_final_certificate_replay": True,
            "valid": True,
        }
        return HeldoutK6CheckpointIndependentVerificationV1(
            document["result_id"],
            base_model.model_id,
            base_audit.audit_id,
            evidence["evidence_id"],
            final_model.model_id,
            final_audit.audit_id,
            content_id(VERIFICATION_DOMAIN, payload),
        )
    except ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error:
        raise
    except Exception as error:
        raise ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error(
            "K6 checkpoint bytes failed independent replay"
        ) from error


__all__ = [
    "ConstructionK7HeldoutK6CheckpointIndependentVerifierV1Error",
    "HeldoutK6CheckpointIndependentVerificationV1",
    "VERIFICATION_DOMAIN",
    "verify_heldout_k6_checkpoint_recertification_bytes_v1",
]
