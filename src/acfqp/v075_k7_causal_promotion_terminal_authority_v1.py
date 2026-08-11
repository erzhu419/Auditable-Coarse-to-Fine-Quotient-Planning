"""Construction-specific budget replay and typed attempt terminal.

The historical V3 budget closure intentionally stopped before a formal
``TerminalArtifactV1`` because no occurrence WorkVector existed.  The K7
causal-promotion accounting path now has that complete 202-record vector.
This additive authority therefore joins two already-frozen facts:

* the sealed business worker reran the exact V3 budget-closure verifier; and
* the occurrence finalizer supplied the complete actual vector/projection.

The result is an attempt-scoped ``ATTEMPT_BUDGET_EXHAUSTED`` noncertificate.
It is deliberately construction-specific.  It does not implement the generic
Phase-3E ``TRUSTED_BUDGET_REPLAY`` authority, close a logical occurrence, pass
either official Gate, or authorize official execution.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    V075_K7_CAUSAL_PROMOTION_BUDGET_REPLAY_ATTESTATION_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_ROUTE_ATTEMPT_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_ROUTE_CONTEXT_V1_DOMAIN,
    V075_K7_CAUSAL_PROMOTION_TERMINAL_DERIVATION_V1_DOMAIN,
    Phase3EIdentityError,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)
from acfqp.routing_v1 import (
    TerminalArtifactV1,
    TerminalClass,
    TerminalCode,
    TypedNotApplicable,
)
from acfqp import v075_live_batched_causal_budget_closure_v3 as budget_v3


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.80"
PROFILE_KEY = "v075_k7_causal_promotion_terminal_authority_v1"

MAXIMUM_PROMOTION_ROUNDS = 2
PROMOTION_DRAWS_PER_ROUND = 2_048
MAXIMUM_TOTAL_PROMOTION_DRAWS = 4_096
PROMOTION_SELECTION_RULE = (
    "MAX_INTERVAL_WIDTH_SUM_THEN_MAX_OTHER_UPPER_THEN_MIN_ROW_ID"
)

TERMINAL_SCOPE = "ROUTE_ATTEMPT"
TERMINAL_CLASS = TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
TERMINAL_CODE = TerminalCode.ATTEMPT_BUDGET_EXHAUSTED

BUDGET_REPLAY_ATTESTATION_DOMAIN = (
    V075_K7_CAUSAL_PROMOTION_BUDGET_REPLAY_ATTESTATION_V1_DOMAIN
)
ROUTE_CONTEXT_DOMAIN = V075_K7_CAUSAL_PROMOTION_ROUTE_CONTEXT_V1_DOMAIN
ROUTE_ATTEMPT_DOMAIN = V075_K7_CAUSAL_PROMOTION_ROUTE_ATTEMPT_V1_DOMAIN
TERMINAL_DERIVATION_DOMAIN = (
    V075_K7_CAUSAL_PROMOTION_TERMINAL_DERIVATION_V1_DOMAIN
)

_BUDGET_DOMAIN_TAGS = {
    "cap_profile": "acfqp:v075-live-causal-promotion-cap-profile:v3",
    "budget_replay": "acfqp:v075-live-causal-promotion-budget-replay:v3",
    "closure": "acfqp:v075-live-causal-promotion-budget-closure:v3",
    "verification": (
        "acfqp:v075-live-causal-promotion-budget-closure-verification:v3"
    ),
    "promotion_bundle_verification": (
        "acfqp:v075-live-batched-causal-promotion-bundle-verification:v3"
    ),
}

_ATTESTATION_ISSUER = object()
_TERMINAL_ISSUER = object()


class V075K7CausalPromotionTerminalAuthorityV1Error(ValueError):
    """The exact budget replay or formal terminal identity was changed."""


def _fail(message: str) -> NoReturn:
    raise V075K7CausalPromotionTerminalAuthorityV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075K7CausalPromotionTerminalAuthorityV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} bytes are absent")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075K7CausalPromotionTerminalAuthorityV1Error(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _local_budget_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = _BUDGET_DOMAIN_TAGS[role]
    except KeyError as error:  # pragma: no cover - closed local registry
        raise V075K7CausalPromotionTerminalAuthorityV1Error(
            "unknown budget replay domain role"
        ) from error
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


_CAP_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "child_operator_profile_id",
    "worker_cap_profile_id",
    "maximum_promotion_rounds",
    "promotion_draws_per_round",
    "maximum_total_promotion_draws",
    "selection_rule",
    "post_run_cap_adjustment_allowed",
    "candidate_required_before_total_lift",
    "cap_profile_id",
}
_REPLAY_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "cap_profile_id",
    "promotion_bundle_id",
    "promotion_bundle_verification_id",
    "final_model_epoch_id",
    "final_proof_id",
    "final_frontier_id",
    "decision_ids",
    "barrier_ids",
    "executed_round_count",
    "executed_promotion_draw_count",
    "registered_round_budget_exactly_replayed",
    "registered_draw_budget_exactly_replayed",
    "final_proof_still_failed",
    "candidate_present",
    "infeasibility_proven",
    "selected_fq9_terminal_class",
    "selected_fq9_terminal_code",
    "trusted_budget_replay_id",
}
_PROMOTION_VERIFICATION_FIELDS = {
    "schema",
    "schema_version",
    "bundle_id",
    "child_execution_bundle_id",
    "final_model_epoch_id",
    "final_proof_id",
    "outcome",
    "executed_round_count",
    "all_decisions_exactly_replayed",
    "all_signed_appends_exactly_replayed",
    "all_model_and_proof_barriers_exactly_replayed",
    "observer_closed",
    "official_execution_allowed",
    "verification_id",
}
_OBSERVER_CLOSURE_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "batch_journal_closure_id",
    "control_closure_id",
    "reconciliation_id",
    "head_ids",
    "intent_ids",
    "append_receipt_ids",
    "support_freeze_ids",
    "support_freeze_count",
    "official_execution_allowed",
    "production_authorizing",
    "process_isolation_provided",
    "python_wrapper_is_not_process_isolation",
    "trusted_in_process_wrapper_order_replayed",
    "single_private_boundary_atomicity_proven",
    "exclusive_signer_ownership_proven",
    "wrapper_signer_reference_cleared_after_both_closures",
    "terminal_class",
}
_CLOSURE_PAYLOAD_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "occurrence_id",
    "promotion_bundle_id",
    "promotion_bundle_verification_id",
    "cap_profile_id",
    "trusted_budget_replay_id",
    "final_model_epoch_id",
    "final_proof_id",
    "batch_journal_closure_id",
    "control_closure_id",
    "control_reconciliation_id",
    "final_head_id",
    "append_count",
    "total_accepted_draw_count",
    "observer_closed_and_exactly_reconciled",
    "terminal_scope",
    "selected_terminal_class",
    "selected_terminal_code",
    "conditional_normalization_target_selected",
    "semantic_terminal_verifier_status",
    "terminal_artifact_issued",
    "terminal_artifact_issuance_allowed",
    "counter_records_issued",
    "work_vector_issued",
    "official_execution_allowed",
}
_CLOSURE_FIELDS = _CLOSURE_PAYLOAD_FIELDS | {
    "cap_profile",
    "trusted_budget_replay",
    "promotion_bundle_verification",
    "observer_closure",
    "closure_id",
}
_VERIFICATION_FIELDS = {
    "schema",
    "schema_version",
    "closure_id",
    "promotion_bundle_id",
    "trusted_budget_replay_id",
    "control_reconciliation_id",
    "final_model_epoch_id",
    "terminal_class",
    "terminal_code",
    "promotion_bundle_exactly_replayed",
    "registered_budget_exactly_replayed",
    "signed_observer_closure_exactly_reconciled",
    "terminal_artifact_issued",
    "official_execution_allowed",
    "verification_id",
}


def _verify_budget_documents(
    closure: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> None:
    """Replay the portable identity and exact registered-cap surface."""

    if type(closure) is not dict or set(closure) != _CLOSURE_FIELDS:
        _fail("budget closure field set changed")
    if type(verification) is not dict or set(verification) != _VERIFICATION_FIELDS:
        _fail("budget closure verification field set changed")
    cap = closure["cap_profile"]
    replay = closure["trusted_budget_replay"]
    promotion_verification = closure["promotion_bundle_verification"]
    observer = closure["observer_closure"]
    if type(cap) is not dict or set(cap) != _CAP_FIELDS:
        _fail("budget cap profile field set changed")
    if type(replay) is not dict or set(replay) != _REPLAY_FIELDS:
        _fail("budget replay field set changed")
    if (
        type(promotion_verification) is not dict
        or set(promotion_verification) != _PROMOTION_VERIFICATION_FIELDS
    ):
        _fail("promotion verification field set changed")
    if type(observer) is not dict or set(observer) != _OBSERVER_CLOSURE_FIELDS:
        _fail("observer closure field set changed")

    cap_payload = dict(cap)
    cap_id = cap_payload.pop("cap_profile_id")
    replay_payload = dict(replay)
    replay_id = replay_payload.pop("trusted_budget_replay_id")
    promotion_payload = dict(promotion_verification)
    promotion_verification_id = promotion_payload.pop("verification_id")
    closure_payload = {key: closure[key] for key in _CLOSURE_PAYLOAD_FIELDS}
    verification_payload = dict(verification)
    verification_id = verification_payload.pop("verification_id")
    for value, label in (
        (cap_id, "cap profile"),
        (replay_id, "trusted budget replay"),
        (promotion_verification_id, "promotion bundle verification"),
        (closure["closure_id"], "budget closure"),
        (verification_id, "budget closure verification"),
    ):
        _cid(value, label)
    if (
        cap_id != _local_budget_id("cap_profile", cap_payload)
        or replay_id != _local_budget_id("budget_replay", replay_payload)
        or promotion_verification_id
        != _local_budget_id("promotion_bundle_verification", promotion_payload)
        or closure["closure_id"]
        != _local_budget_id("closure", closure_payload)
        or verification_id
        != _local_budget_id("verification", verification_payload)
    ):
        _fail("budget replay content identity changed")

    decisions = replay["decision_ids"]
    barriers = replay["barrier_ids"]
    heads = observer["head_ids"]
    intents = observer["intent_ids"]
    receipts = observer["append_receipt_ids"]
    freezes = observer["support_freeze_ids"]
    if not all(type(rows) is list for rows in (decisions, barriers, heads, intents, receipts, freezes)):
        _fail("budget replay ordered evidence must be lists")
    for value in (*decisions, *barriers, *heads, *intents, *receipts, *freezes):
        _cid(value, "budget replay ordered evidence")
    if (
        len(decisions) != MAXIMUM_PROMOTION_ROUNDS
        or len(barriers) != MAXIMUM_PROMOTION_ROUNDS
        or len(set(decisions)) != len(decisions)
        or len(set(barriers)) != len(barriers)
        or cap["maximum_promotion_rounds"] != MAXIMUM_PROMOTION_ROUNDS
        or cap["promotion_draws_per_round"] != PROMOTION_DRAWS_PER_ROUND
        or cap["maximum_total_promotion_draws"]
        != MAXIMUM_TOTAL_PROMOTION_DRAWS
        or cap["selection_rule"] != PROMOTION_SELECTION_RULE
        or cap["post_run_cap_adjustment_allowed"] is not False
        or cap["candidate_required_before_total_lift"] is not True
        or replay["executed_round_count"] != MAXIMUM_PROMOTION_ROUNDS
        or replay["executed_promotion_draw_count"]
        != MAXIMUM_TOTAL_PROMOTION_DRAWS
        or replay["registered_round_budget_exactly_replayed"] is not True
        or replay["registered_draw_budget_exactly_replayed"] is not True
        or replay["final_proof_still_failed"] is not True
        or replay["candidate_present"] is not False
        or replay["infeasibility_proven"] is not False
        or replay["selected_fq9_terminal_class"] != TERMINAL_CLASS.value
        or replay["selected_fq9_terminal_code"] != TERMINAL_CODE.value
        or promotion_verification["outcome"] != "PROMOTION_BUDGET_EXHAUSTED"
        or promotion_verification["executed_round_count"]
        != MAXIMUM_PROMOTION_ROUNDS
        or promotion_verification["all_decisions_exactly_replayed"] is not True
        or promotion_verification["all_signed_appends_exactly_replayed"] is not True
        or promotion_verification[
            "all_model_and_proof_barriers_exactly_replayed"
        ]
        is not True
        or promotion_verification["observer_closed"] is not False
        or promotion_verification["official_execution_allowed"] is not False
        or observer["support_freeze_count"] != len(freezes)
        or observer["official_execution_allowed"] is not False
        or observer["production_authorizing"] is not False
        or closure["observer_closed_and_exactly_reconciled"] is not True
        or closure["terminal_scope"] != TERMINAL_SCOPE
        or closure["selected_terminal_class"] != TERMINAL_CLASS.value
        or closure["selected_terminal_code"] != TERMINAL_CODE.value
        or closure["conditional_normalization_target_selected"] is not True
        or closure["terminal_artifact_issued"] is not False
        or closure["terminal_artifact_issuance_allowed"] is not False
        or closure["counter_records_issued"] != 0
        or closure["work_vector_issued"] is not False
        or closure["official_execution_allowed"] is not False
        or verification["terminal_class"] != TERMINAL_CLASS.value
        or verification["terminal_code"] != TERMINAL_CODE.value
        or verification["promotion_bundle_exactly_replayed"] is not True
        or verification["registered_budget_exactly_replayed"] is not True
        or verification[
            "signed_observer_closure_exactly_reconciled"
        ]
        is not True
        or verification["terminal_artifact_issued"] is not False
        or verification["official_execution_allowed"] is not False
    ):
        _fail("registered budget replay or historical boundary changed")
    if (
        closure["cap_profile_id"] != cap_id
        or closure["trusted_budget_replay_id"] != replay_id
        or closure["promotion_bundle_id"] != replay["promotion_bundle_id"]
        or closure["promotion_bundle_verification_id"]
        != promotion_verification_id
        or replay["cap_profile_id"] != cap_id
        or replay["promotion_bundle_verification_id"]
        != promotion_verification_id
        or promotion_verification["bundle_id"] != closure["promotion_bundle_id"]
        or closure["final_model_epoch_id"] != replay["final_model_epoch_id"]
        or closure["final_model_epoch_id"]
        != promotion_verification["final_model_epoch_id"]
        or closure["final_proof_id"] != replay["final_proof_id"]
        or closure["final_proof_id"] != promotion_verification["final_proof_id"]
        or closure["batch_journal_closure_id"]
        != observer["batch_journal_closure_id"]
        or closure["control_closure_id"] != observer["control_closure_id"]
        or closure["control_reconciliation_id"] != observer["reconciliation_id"]
        or closure["append_count"] != len(receipts)
        or verification["closure_id"] != closure["closure_id"]
        or verification["promotion_bundle_id"] != closure["promotion_bundle_id"]
        or verification["trusted_budget_replay_id"] != replay_id
        or verification["control_reconciliation_id"]
        != closure["control_reconciliation_id"]
        or verification["final_model_epoch_id"]
        != closure["final_model_epoch_id"]
    ):
        _fail("budget closure identity graph crossed")


_ATTESTATION_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "occurrence_id",
    "budget_closure_id",
    "budget_closure_verification_id",
    "cap_profile_id",
    "trusted_budget_replay_id",
    "promotion_bundle_id",
    "final_model_epoch_id",
    "final_proof_id",
    "final_frontier_id",
    "executed_round_count",
    "executed_promotion_draw_count",
    "terminal_scope",
    "terminal_class",
    "terminal_code",
    "budget_closure",
    "budget_closure_verification",
    "sealed_worker_exact_budget_closure_verification_consumed",
    "registered_cap_replayed_before_terminal_mapping",
    "worker_outcome_string_used_as_authority",
    "construction_specific_semantic_authority",
    "generic_trusted_budget_replay_v1_implemented",
    "logical_occurrence_closed",
    "campaign_closure_issued",
    "official_execution_allowed",
    "budget_replay_attestation_id",
}


@dataclass(frozen=True, slots=True)
class CausalPromotionBudgetReplayAttestationV1:
    _issuer: InitVar[object]
    _canonical_bytes: bytes = field(repr=False)
    _attestation_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ATTESTATION_ISSUER:
            _fail("budget replay attestation is caller-minted")
        document = _strict_document(self._canonical_bytes, "budget replay attestation")
        if set(document) != _ATTESTATION_FIELDS:
            _fail("budget replay attestation field set changed")
        supplied = document["budget_replay_attestation_id"]
        payload = dict(document)
        payload.pop("budget_replay_attestation_id")
        expected = content_id(BUDGET_REPLAY_ATTESTATION_DOMAIN, payload)
        if supplied != expected:
            _fail("budget replay attestation content ID changed")
        _verify_attestation_payload(payload)
        object.__setattr__(self, "_attestation_id", expected)

    @property
    def attestation_id(self) -> str:
        return self._attestation_id

    @property
    def canonical_bytes(self) -> bytes:
        return self._canonical_bytes

    def to_document(self) -> dict[str, Any]:
        return _strict_document(self._canonical_bytes, "budget replay attestation")


def _verify_attestation_payload(payload: Mapping[str, Any]) -> None:
    closure = payload["budget_closure"]
    verification = payload["budget_closure_verification"]
    _verify_budget_documents(closure, verification)
    replay = closure["trusted_budget_replay"]
    if (
        payload["schema"]
        != "acfqp.v075_k7_causal_promotion_budget_replay_attestation.v1"
        or payload["schema_version"] != SCHEMA_VERSION
        or payload["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or payload["profile_key"] != PROFILE_KEY
        or payload["occurrence_id"] != closure["occurrence_id"]
        or payload["budget_closure_id"] != closure["closure_id"]
        or payload["budget_closure_verification_id"]
        != verification["verification_id"]
        or payload["cap_profile_id"] != closure["cap_profile_id"]
        or payload["trusted_budget_replay_id"]
        != closure["trusted_budget_replay_id"]
        or payload["promotion_bundle_id"] != closure["promotion_bundle_id"]
        or payload["final_model_epoch_id"] != closure["final_model_epoch_id"]
        or payload["final_proof_id"] != closure["final_proof_id"]
        or payload["final_frontier_id"] != replay["final_frontier_id"]
        or payload["executed_round_count"] != MAXIMUM_PROMOTION_ROUNDS
        or payload["executed_promotion_draw_count"]
        != MAXIMUM_TOTAL_PROMOTION_DRAWS
        or payload["terminal_scope"] != TERMINAL_SCOPE
        or payload["terminal_class"] != TERMINAL_CLASS.value
        or payload["terminal_code"] != TERMINAL_CODE.value
        or payload[
            "sealed_worker_exact_budget_closure_verification_consumed"
        ]
        is not True
        or payload["registered_cap_replayed_before_terminal_mapping"] is not True
        or payload["worker_outcome_string_used_as_authority"] is not False
        or payload["construction_specific_semantic_authority"] is not True
        or payload["generic_trusted_budget_replay_v1_implemented"] is not False
        or payload["logical_occurrence_closed"] is not False
        or payload["campaign_closure_issued"] is not False
        or payload["official_execution_allowed"] is not False
    ):
        _fail("budget replay attestation semantic payload changed")
    for key in (
        "occurrence_id",
        "budget_closure_id",
        "budget_closure_verification_id",
        "cap_profile_id",
        "trusted_budget_replay_id",
        "promotion_bundle_id",
        "final_model_epoch_id",
        "final_proof_id",
        "final_frontier_id",
    ):
        _cid(payload[key], f"budget replay attestation {key}")


def issue_v075_k7_causal_promotion_budget_replay_attestation_v1(
    *,
    budget_closure: budget_v3.V075LiveBatchedCausalBudgetClosedOccurrenceV3,
    budget_closure_verification: (
        budget_v3.V075LiveBatchedCausalBudgetClosureVerificationV3
    ),
) -> CausalPromotionBudgetReplayAttestationV1:
    """Consume the exact V3 verification issued by the same sealed run.

    ``close_v075_live_batched_causal_budget_exhausted_v3`` already performs
    the full promotion/observer replay before it issues these two objects.
    Reexecuting that expensive verifier here would duplicate business work
    without adding an independent source.  This successor checks the exact
    issuer objects and their complete identity join, then freezes the portable
    terminal-mapping evidence.
    """

    if (
        type(budget_closure)
        is not budget_v3.V075LiveBatchedCausalBudgetClosedOccurrenceV3
        or type(budget_closure_verification)
        is not budget_v3.V075LiveBatchedCausalBudgetClosureVerificationV3
    ):
        _fail("budget replay attestation requires exact V3 objects")
    if (
        budget_closure_verification.closure_id != budget_closure.closure_id
        or budget_closure_verification.promotion_bundle_id
        != budget_closure.promotion_bundle.bundle_id
        or budget_closure_verification.trusted_budget_replay_id
        != budget_closure.budget_replay.replay_id
        or budget_closure_verification.control_reconciliation_id
        != budget_closure.observer_closure.reconciliation.reconciliation_id
        or budget_closure_verification.final_model_epoch_id
        != budget_closure.promotion_bundle.final_epoch.model_epoch_id
        or budget_closure_verification.terminal_class is not TERMINAL_CLASS
        or budget_closure_verification.terminal_code is not TERMINAL_CODE
    ):
        _fail("sealed worker budget verification crossed artifacts")
    closure_document = budget_closure.to_document()
    verification_document = budget_closure_verification.to_document()
    _verify_budget_documents(closure_document, verification_document)
    replay = closure_document["trusted_budget_replay"]
    payload = {
        "schema": "acfqp.v075_k7_causal_promotion_budget_replay_attestation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "occurrence_id": closure_document["occurrence_id"],
        "budget_closure_id": closure_document["closure_id"],
        "budget_closure_verification_id": verification_document["verification_id"],
        "cap_profile_id": closure_document["cap_profile_id"],
        "trusted_budget_replay_id": closure_document["trusted_budget_replay_id"],
        "promotion_bundle_id": closure_document["promotion_bundle_id"],
        "final_model_epoch_id": closure_document["final_model_epoch_id"],
        "final_proof_id": closure_document["final_proof_id"],
        "final_frontier_id": replay["final_frontier_id"],
        "executed_round_count": replay["executed_round_count"],
        "executed_promotion_draw_count": replay["executed_promotion_draw_count"],
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS.value,
        "terminal_code": TERMINAL_CODE.value,
        "budget_closure": closure_document,
        "budget_closure_verification": verification_document,
        "sealed_worker_exact_budget_closure_verification_consumed": True,
        "registered_cap_replayed_before_terminal_mapping": True,
        "worker_outcome_string_used_as_authority": False,
        "construction_specific_semantic_authority": True,
        "generic_trusted_budget_replay_v1_implemented": False,
        "logical_occurrence_closed": False,
        "campaign_closure_issued": False,
        "official_execution_allowed": False,
    }
    document = {
        **payload,
        "budget_replay_attestation_id": content_id(
            BUDGET_REPLAY_ATTESTATION_DOMAIN, payload
        ),
    }
    return CausalPromotionBudgetReplayAttestationV1(
        _ATTESTATION_ISSUER,
        canonical_json_bytes(document),
    )


def verify_v075_k7_causal_promotion_budget_replay_attestation_document_v1(
    document: Mapping[str, Any],
) -> dict[str, Any]:
    """Portable replay of the attestation identity and registered cap facts."""

    if type(document) is not dict or set(document) != _ATTESTATION_FIELDS:
        _fail("budget replay attestation document field set changed")
    payload = dict(document)
    supplied = payload.pop("budget_replay_attestation_id")
    if supplied != content_id(BUDGET_REPLAY_ATTESTATION_DOMAIN, payload):
        _fail("budget replay attestation document content ID changed")
    _verify_attestation_payload(payload)
    return dict(document)


def _route_context_document(
    *,
    occurrence_id: str,
    accounted_occurrence_id: str,
    supervised_execution_id: str,
    budget_replay_attestation_id: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_k7_causal_promotion_route_context.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": occurrence_id,
        "accounted_occurrence_id": accounted_occurrence_id,
        "supervised_execution_id": supervised_execution_id,
        "budget_replay_attestation_id": budget_replay_attestation_id,
        "route_kind": "ABSTRACT_FAILED_PREFIX",
        "terminal_scope": TERMINAL_SCOPE,
        "construction_specific_context": True,
        "generic_marginal_route_decision_present": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "route_decision_context_id": content_id(ROUTE_CONTEXT_DOMAIN, payload),
    }


def _route_attempt_document(
    *,
    occurrence_id: str,
    route_decision_context_id: str,
    budget_replay_attestation_id: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_k7_causal_promotion_route_attempt.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": occurrence_id,
        "route_decision_context_id": route_decision_context_id,
        "route_attempt_index": 1,
        "budget_replay_attestation_id": budget_replay_attestation_id,
        "terminal_class": TERMINAL_CLASS.value,
        "terminal_code": TERMINAL_CODE.value,
        "logical_occurrence_closed": False,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "route_attempt_id": content_id(ROUTE_ATTEMPT_DOMAIN, payload),
    }


def _terminal_derivation_document(
    *,
    occurrence_id: str,
    route_context_id: str,
    route_attempt_id: str,
    budget_attestation: Mapping[str, Any],
    work_vector_id: str,
    comparison_vector_id: str,
    projection_proof_id: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.v075_k7_causal_promotion_terminal_derivation.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "logical_occurrence_id": occurrence_id,
        "route_decision_context_id": route_context_id,
        "route_attempt_id": route_attempt_id,
        "budget_replay_attestation_id": (
            budget_attestation["budget_replay_attestation_id"]
        ),
        "budget_closure_id": budget_attestation["budget_closure_id"],
        "budget_closure_verification_id": (
            budget_attestation["budget_closure_verification_id"]
        ),
        "trusted_budget_replay_id": budget_attestation["trusted_budget_replay_id"],
        "actual_work_vector_id": work_vector_id,
        "actual_comparison_vector_id": comparison_vector_id,
        "actual_projection_proof_id": projection_proof_id,
        "counter_record_count": 202,
        "projection_term_count": 182,
        "route_attempt_count": 1,
        "route_success_count": 0,
        "route_failure_count": 1,
        "terminal_scope": TERMINAL_SCOPE,
        "terminal_class": TERMINAL_CLASS.value,
        "terminal_code": TERMINAL_CODE.value,
        "sealed_worker_budget_replay_joined_to_formal_actual_work": True,
        "failed_route_work_preserved": True,
        "worker_outcome_string_used_as_authority": False,
        "generic_trusted_budget_replay_v1_implemented": False,
        "construction_specific_terminal_authority": True,
        "terminal_is_plan_certificate": False,
        "terminal_is_infeasibility_certificate": False,
        "logical_occurrence_closed": False,
        "campaign_closure_issued": False,
        "counter_completeness_gate_passed": False,
        "workload_economics_gate_passed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "official_execution_allowed": False,
    }
    return {
        **payload,
        "terminal_derivation_attestation_id": content_id(
            TERMINAL_DERIVATION_DOMAIN, payload
        ),
    }


@dataclass(frozen=True, slots=True)
class CausalPromotionBudgetTerminalAuthorityV1:
    _issuer: InitVar[object]
    _route_context_bytes: bytes = field(repr=False)
    _route_attempt_bytes: bytes = field(repr=False)
    _derivation_bytes: bytes = field(repr=False)
    terminal_artifact: TerminalArtifactV1

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _TERMINAL_ISSUER:
            _fail("causal-promotion terminal authority is caller-minted")
        context = _strict_document(self._route_context_bytes, "route context")
        attempt = _strict_document(self._route_attempt_bytes, "route attempt")
        derivation = _strict_document(self._derivation_bytes, "terminal derivation")
        verify_v075_k7_causal_promotion_terminal_documents_v1(
            route_context=context,
            route_attempt=attempt,
            terminal_derivation=derivation,
            terminal_artifact=self.terminal_artifact.to_dict(),
        )

    @property
    def route_context(self) -> dict[str, Any]:
        return _strict_document(self._route_context_bytes, "route context")

    @property
    def route_attempt(self) -> dict[str, Any]:
        return _strict_document(self._route_attempt_bytes, "route attempt")

    @property
    def terminal_derivation(self) -> dict[str, Any]:
        return _strict_document(self._derivation_bytes, "terminal derivation")

    def to_role_document(self, *, output_bytes: int) -> dict[str, Any]:
        if type(output_bytes) is not int or output_bytes < 0:
            _fail("terminal output-byte candidate is invalid")
        return {
            "artifact_role": "TERMINAL_ARTIFACT",
            "schema": "acfqp.v075_k7_causal_promotion_terminal_artifact_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "io.output_bytes": output_bytes,
            "route_decision_context": self.route_context,
            "route_attempt": self.route_attempt,
            "budget_terminal_derivation_attestation": self.terminal_derivation,
            "terminal_artifact": self.terminal_artifact.to_dict(),
            "semantic_terminal_artifact_issued": True,
            "construction_specific_terminal_authority": True,
            "generic_trusted_budget_replay_v1_implemented": False,
            "logical_occurrence_closed": False,
            "campaign_closure_issued": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "official_execution_allowed": False,
        }


def issue_v075_k7_causal_promotion_budget_terminal_v1(
    *,
    budget_replay_attestation: Mapping[str, Any],
    occurrence_id: str,
    accounted_occurrence_id: str,
    supervised_execution_id: str,
    work_vector_id: str,
    comparison_vector_id: str,
    projection_proof_id: str,
) -> CausalPromotionBudgetTerminalAuthorityV1:
    attestation = verify_v075_k7_causal_promotion_budget_replay_attestation_document_v1(
        budget_replay_attestation
    )
    for value, label in (
        (occurrence_id, "terminal occurrence"),
        (accounted_occurrence_id, "terminal accounted occurrence"),
        (supervised_execution_id, "terminal supervised execution"),
        (work_vector_id, "terminal WorkVector"),
        (comparison_vector_id, "terminal ComparisonVector"),
        (projection_proof_id, "terminal projection proof"),
    ):
        _cid(value, label)
    if occurrence_id != attestation["occurrence_id"]:
        _fail("terminal occurrence crossed budget replay evidence")
    context = _route_context_document(
        occurrence_id=occurrence_id,
        accounted_occurrence_id=accounted_occurrence_id,
        supervised_execution_id=supervised_execution_id,
        budget_replay_attestation_id=attestation["budget_replay_attestation_id"],
    )
    attempt = _route_attempt_document(
        occurrence_id=occurrence_id,
        route_decision_context_id=context["route_decision_context_id"],
        budget_replay_attestation_id=attestation["budget_replay_attestation_id"],
    )
    derivation = _terminal_derivation_document(
        occurrence_id=occurrence_id,
        route_context_id=context["route_decision_context_id"],
        route_attempt_id=attempt["route_attempt_id"],
        budget_attestation=attestation,
        work_vector_id=work_vector_id,
        comparison_vector_id=comparison_vector_id,
        projection_proof_id=projection_proof_id,
    )
    terminal = TerminalArtifactV1(
        terminal_scope=TERMINAL_SCOPE,
        terminal_class=TERMINAL_CLASS,
        terminal_code=TERMINAL_CODE,
        route_decision_context_id=context["route_decision_context_id"],
        logical_occurrence_id=occurrence_id,
        route_attempt_id=attempt["route_attempt_id"],
        decision_point_id=TypedNotApplicable(
            "construction budget closure has no marginal route decision point"
        ),
        transaction_id=TypedNotApplicable(
            "construction promotion rounds are not Phase-3E local transactions"
        ),
        actual_work_vector_id=work_vector_id,
        evidence_attestation_ids=tuple(
            sorted(
                (
                    attestation["budget_replay_attestation_id"],
                    derivation["terminal_derivation_attestation_id"],
                )
            )
        ),
        actual_comparison_vector_id=comparison_vector_id,
        actual_projection_proof_id=projection_proof_id,
        marginal_work_aggregation_proof_id=TypedNotApplicable(
            "construction failed-prefix work is one occurrence vector"
        ),
        route_decision_freeze_attestation_id=TypedNotApplicable(
            "construction path did not perform dynamic marginal routing"
        ),
        access_event_log_id=TypedNotApplicable(
            "construction path predates the official access-order runner"
        ),
    )
    return CausalPromotionBudgetTerminalAuthorityV1(
        _TERMINAL_ISSUER,
        canonical_json_bytes(context),
        canonical_json_bytes(attempt),
        canonical_json_bytes(derivation),
        terminal,
    )


def verify_v075_k7_causal_promotion_terminal_documents_v1(
    *,
    route_context: Mapping[str, Any],
    route_attempt: Mapping[str, Any],
    terminal_derivation: Mapping[str, Any],
    terminal_artifact: Mapping[str, Any],
) -> TerminalArtifactV1:
    """Replay all construction-specific terminal identities and joins."""

    context_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "logical_occurrence_id",
        "accounted_occurrence_id",
        "supervised_execution_id",
        "budget_replay_attestation_id",
        "route_kind",
        "terminal_scope",
        "construction_specific_context",
        "generic_marginal_route_decision_present",
        "official_execution_allowed",
        "route_decision_context_id",
    }
    attempt_fields = {
        "schema",
        "schema_version",
        "profile_key",
        "logical_occurrence_id",
        "route_decision_context_id",
        "route_attempt_index",
        "budget_replay_attestation_id",
        "terminal_class",
        "terminal_code",
        "logical_occurrence_closed",
        "official_execution_allowed",
        "route_attempt_id",
    }
    derivation_fields = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "logical_occurrence_id",
        "route_decision_context_id",
        "route_attempt_id",
        "budget_replay_attestation_id",
        "budget_closure_id",
        "budget_closure_verification_id",
        "trusted_budget_replay_id",
        "actual_work_vector_id",
        "actual_comparison_vector_id",
        "actual_projection_proof_id",
        "counter_record_count",
        "projection_term_count",
        "route_attempt_count",
        "route_success_count",
        "route_failure_count",
        "terminal_scope",
        "terminal_class",
        "terminal_code",
        "sealed_worker_budget_replay_joined_to_formal_actual_work",
        "failed_route_work_preserved",
        "worker_outcome_string_used_as_authority",
        "generic_trusted_budget_replay_v1_implemented",
        "construction_specific_terminal_authority",
        "terminal_is_plan_certificate",
        "terminal_is_infeasibility_certificate",
        "logical_occurrence_closed",
        "campaign_closure_issued",
        "counter_completeness_gate_passed",
        "workload_economics_gate_passed",
        "official_scalar_cost",
        "official_N_break_even",
        "official_execution_allowed",
        "terminal_derivation_attestation_id",
    }
    try:
        require_exact_fields(route_context, context_fields, context="route context")
        require_exact_fields(route_attempt, attempt_fields, context="route attempt")
        require_exact_fields(
            terminal_derivation,
            derivation_fields,
            context="terminal derivation",
        )
    except (TypeError, ValueError) as error:
        raise V075K7CausalPromotionTerminalAuthorityV1Error(str(error)) from error
    context_payload = dict(route_context)
    context_id = context_payload.pop("route_decision_context_id")
    attempt_payload = dict(route_attempt)
    attempt_id = attempt_payload.pop("route_attempt_id")
    derivation_payload = dict(terminal_derivation)
    derivation_id = derivation_payload.pop("terminal_derivation_attestation_id")
    if (
        context_id != content_id(ROUTE_CONTEXT_DOMAIN, context_payload)
        or attempt_id != content_id(ROUTE_ATTEMPT_DOMAIN, attempt_payload)
        or derivation_id
        != content_id(TERMINAL_DERIVATION_DOMAIN, derivation_payload)
    ):
        _fail("construction terminal content identity changed")
    terminal = TerminalArtifactV1.from_dict(terminal_artifact)
    if (
        route_context["schema"]
        != "acfqp.v075_k7_causal_promotion_route_context.v1"
        or route_context["schema_version"] != SCHEMA_VERSION
        or route_context["profile_key"] != PROFILE_KEY
        or route_context["route_kind"] != "ABSTRACT_FAILED_PREFIX"
        or route_context["terminal_scope"] != TERMINAL_SCOPE
        or route_context["construction_specific_context"] is not True
        or route_context["generic_marginal_route_decision_present"] is not False
        or route_context["official_execution_allowed"] is not False
        or route_attempt["schema"]
        != "acfqp.v075_k7_causal_promotion_route_attempt.v1"
        or route_attempt["route_attempt_index"] != 1
        or route_attempt["terminal_class"] != TERMINAL_CLASS.value
        or route_attempt["terminal_code"] != TERMINAL_CODE.value
        or route_attempt["logical_occurrence_closed"] is not False
        or route_attempt["official_execution_allowed"] is not False
        or terminal_derivation["schema"]
        != "acfqp.v075_k7_causal_promotion_terminal_derivation.v1"
        or terminal_derivation["counter_record_count"] != 202
        or terminal_derivation["projection_term_count"] != 182
        or (
            terminal_derivation["route_attempt_count"],
            terminal_derivation["route_success_count"],
            terminal_derivation["route_failure_count"],
        )
        != (1, 0, 1)
        or terminal_derivation["terminal_scope"] != TERMINAL_SCOPE
        or terminal_derivation["terminal_class"] != TERMINAL_CLASS.value
        or terminal_derivation["terminal_code"] != TERMINAL_CODE.value
        or terminal_derivation[
            "sealed_worker_budget_replay_joined_to_formal_actual_work"
        ]
        is not True
        or terminal_derivation["failed_route_work_preserved"] is not True
        or terminal_derivation["worker_outcome_string_used_as_authority"] is not False
        or terminal_derivation["generic_trusted_budget_replay_v1_implemented"] is not False
        or terminal_derivation["construction_specific_terminal_authority"] is not True
        or terminal_derivation["terminal_is_plan_certificate"] is not False
        or terminal_derivation["terminal_is_infeasibility_certificate"] is not False
        or terminal_derivation["logical_occurrence_closed"] is not False
        or terminal_derivation["campaign_closure_issued"] is not False
        or terminal_derivation["counter_completeness_gate_passed"] is not False
        or terminal_derivation["workload_economics_gate_passed"] is not False
        or terminal_derivation["official_scalar_cost"] is not None
        or terminal_derivation["official_N_break_even"] is not None
        or terminal_derivation["official_execution_allowed"] is not False
    ):
        _fail("construction terminal semantic contract changed")
    occurrence_id = route_context["logical_occurrence_id"]
    budget_attestation_id = route_context["budget_replay_attestation_id"]
    if (
        route_attempt["logical_occurrence_id"] != occurrence_id
        or route_attempt["route_decision_context_id"] != context_id
        or route_attempt["budget_replay_attestation_id"] != budget_attestation_id
        or terminal_derivation["logical_occurrence_id"] != occurrence_id
        or terminal_derivation["route_decision_context_id"] != context_id
        or terminal_derivation["route_attempt_id"] != attempt_id
        or terminal_derivation["budget_replay_attestation_id"]
        != budget_attestation_id
        or terminal.terminal_scope != TERMINAL_SCOPE
        or terminal.terminal_class is not TERMINAL_CLASS
        or terminal.terminal_code is not TERMINAL_CODE
        or terminal.route_decision_context_id != context_id
        or terminal.logical_occurrence_id != occurrence_id
        or terminal.route_attempt_id != attempt_id
        or terminal.actual_work_vector_id
        != terminal_derivation["actual_work_vector_id"]
        or terminal.actual_comparison_vector_id
        != terminal_derivation["actual_comparison_vector_id"]
        or terminal.actual_projection_proof_id
        != terminal_derivation["actual_projection_proof_id"]
        or terminal.evidence_attestation_ids
        != tuple(sorted((budget_attestation_id, derivation_id)))
    ):
        _fail("construction terminal identity graph crossed")
    return terminal


__all__ = (
    "BUDGET_REPLAY_ATTESTATION_DOMAIN",
    "CausalPromotionBudgetReplayAttestationV1",
    "CausalPromotionBudgetTerminalAuthorityV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "ROUTE_ATTEMPT_DOMAIN",
    "ROUTE_CONTEXT_DOMAIN",
    "SCHEMA_VERSION",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "TERMINAL_DERIVATION_DOMAIN",
    "V075K7CausalPromotionTerminalAuthorityV1Error",
    "issue_v075_k7_causal_promotion_budget_replay_attestation_v1",
    "issue_v075_k7_causal_promotion_budget_terminal_v1",
    "verify_v075_k7_causal_promotion_budget_replay_attestation_document_v1",
    "verify_v075_k7_causal_promotion_terminal_documents_v1",
)
