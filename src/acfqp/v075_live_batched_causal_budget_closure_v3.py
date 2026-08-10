"""Observer closure and typed noncertificate target after promotion exhaustion.

The V3 causal promotion profile has a frozen two-round budget.  When both
registered +2048 extensions have been executed and the exact numerical proof
still exposes a failed frontier, the observer must be closed and the attempt
must not be reported as a plan candidate or infeasibility certificate.

This module performs that closure and freezes a trusted budget-replay evidence
chain selecting the FQ9 target
``ATTEMPT_CLOSURE_NONCERTIFICATE / ATTEMPT_BUDGET_EXHAUSTED``.  It deliberately
does not mint ``TerminalArtifactV1``: the official semantic verifier still
marks ``TRUSTED_BUDGET_REPLAY`` unimplemented, and no authoritative WorkVector
exists yet.  The output is therefore a typed construction target awaiting the
K7 accounting and terminal-authority stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp.routing_v1 import TerminalClass, TerminalCode
from acfqp import v075_batch_native_planning_backend_v2 as planning
from acfqp import v075_live_batched_causal_promotion_v3 as promotion
from acfqp import v075_observer_signed_batch_control_authority_v2 as control


SCHEMA_VERSION = "3.0.0"
PROPOSED_CONTRACT_VERSION = "1.64.0"
PROFILE_KEY = "v075_live_batched_causal_budget_closure_v3"
MAX_CANONICAL_INPUT_BYTES = 192 * 1024 * 1024

TERMINAL_SCOPE = "ROUTE_ATTEMPT"
TERMINAL_CLASS = TerminalClass.ATTEMPT_CLOSURE_NONCERTIFICATE
TERMINAL_CODE = TerminalCode.ATTEMPT_BUDGET_EXHAUSTED
SEMANTIC_TERMINAL_VERIFIER_STATUS = "TRUSTED_BUDGET_REPLAY_NOT_IMPLEMENTED"

TERMINAL_ARTIFACT_ISSUANCE_ALLOWED = False
COUNTER_RECORD_ISSUANCE_ALLOWED = False
WORK_VECTOR_ISSUANCE_ALLOWED = False
OFFICIAL_EXECUTION_ALLOWED = False

DOMAIN_TAGS = {
    "cap_profile": "acfqp:v075-live-causal-promotion-cap-profile:v3",
    "budget_replay": "acfqp:v075-live-causal-promotion-budget-replay:v3",
    "closure": "acfqp:v075-live-causal-promotion-budget-closure:v3",
    "verification": (
        "acfqp:v075-live-causal-promotion-budget-closure-verification:v3"
    ),
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("causal promotion budget closure domains must be unique")


class V075LiveBatchedCausalBudgetClosureV3InvariantViolation(ValueError):
    """The cap, bundle, signed closure, or noncertificate target changed."""


def _fail(message: str) -> NoReturn:
    raise V075LiveBatchedCausalBudgetClosureV3InvariantViolation(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075LiveBatchedCausalBudgetClosureV3InvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075LiveBatchedCausalBudgetClosureV3InvariantViolation(
            str(error)
        ) from error


def _strict_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_CANONICAL_INPUT_BYTES:
        _fail(f"{label} bytes are absent or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075LiveBatchedCausalBudgetClosureV3InvariantViolation(
            f"{label} is not strict canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical JSON object")
    return document


_CAP_ISSUER = object()
_REPLAY_ISSUER = object()
_CLOSURE_ISSUER = object()
_VERIFICATION_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionCapProfileV3:
    _issuer: object = field(repr=False, compare=False)
    child_operator_profile_id: str
    worker_cap_profile_id: str
    maximum_promotion_rounds: int
    promotion_draws_per_round: int
    selection_rule: str
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.child_operator_profile_id, "promotion child operator profile"),
            (self.worker_cap_profile_id, "promotion worker cap profile"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _CAP_ISSUER
            or self.maximum_promotion_rounds
            != promotion.MAXIMUM_PROMOTION_ROUNDS
            or self.promotion_draws_per_round != promotion.PROMOTION_DRAWS
            or self.selection_rule != promotion.PROMOTION_SELECTION_RULE
        ):
            _fail("promotion cap profile changed")
        object.__setattr__(
            self,
            "_profile_id",
            _hash("cap_profile", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_causal_promotion_cap_profile.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "child_operator_profile_id": self.child_operator_profile_id,
            "worker_cap_profile_id": self.worker_cap_profile_id,
            "maximum_promotion_rounds": self.maximum_promotion_rounds,
            "promotion_draws_per_round": self.promotion_draws_per_round,
            "maximum_total_promotion_draws": (
                self.maximum_promotion_rounds * self.promotion_draws_per_round
            ),
            "selection_rule": self.selection_rule,
            "post_run_cap_adjustment_allowed": False,
            "candidate_required_before_total_lift": True,
        }

    @property
    def profile_id(self) -> str:
        return self._profile_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cap_profile_id": self.profile_id}


def freeze_v075_live_batched_causal_promotion_cap_profile_v3(
    bundle: promotion.V075LiveBatchedCausalPromotionBundleV3,
) -> V075LiveBatchedCausalPromotionCapProfileV3:
    if type(bundle) is not promotion.V075LiveBatchedCausalPromotionBundleV3:
        _fail("promotion cap profile requires one exact promotion bundle")
    child_profile = bundle.child_execution_bundle.authorization.profile
    return V075LiveBatchedCausalPromotionCapProfileV3(
        _CAP_ISSUER,
        child_profile.profile_id,
        child_profile.cap_profile_id,
        promotion.MAXIMUM_PROMOTION_ROUNDS,
        promotion.PROMOTION_DRAWS,
        promotion.PROMOTION_SELECTION_RULE,
    )


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalPromotionBudgetReplayV3:
    _issuer: object = field(repr=False, compare=False)
    cap_profile_id: str
    promotion_bundle_id: str
    promotion_bundle_verification_id: str
    final_model_epoch_id: str
    final_proof_id: str
    final_frontier_id: str
    decision_ids: tuple[str, ...]
    barrier_ids: tuple[str, ...]
    executed_round_count: int
    executed_promotion_draw_count: int
    _replay_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.cap_profile_id, "budget replay cap profile"),
            (self.promotion_bundle_id, "budget replay bundle"),
            (
                self.promotion_bundle_verification_id,
                "budget replay bundle verification",
            ),
            (self.final_model_epoch_id, "budget replay final epoch"),
            (self.final_proof_id, "budget replay final proof"),
            (self.final_frontier_id, "budget replay final frontier"),
            *((value, "budget replay decision") for value in self.decision_ids),
            *((value, "budget replay barrier") for value in self.barrier_ids),
        ):
            _cid(value, label)
        if (
            self._issuer is not _REPLAY_ISSUER
            or type(self.decision_ids) is not tuple
            or type(self.barrier_ids) is not tuple
            or self.executed_round_count != promotion.MAXIMUM_PROMOTION_ROUNDS
            or len(self.decision_ids) != self.executed_round_count
            or len(self.barrier_ids) != self.executed_round_count
            or self.executed_promotion_draw_count
            != self.executed_round_count * promotion.PROMOTION_DRAWS
        ):
            _fail("promotion budget replay is malformed")
        object.__setattr__(
            self,
            "_replay_id",
            _hash("budget_replay", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_live_causal_promotion_budget_replay.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "cap_profile_id": self.cap_profile_id,
            "promotion_bundle_id": self.promotion_bundle_id,
            "promotion_bundle_verification_id": (
                self.promotion_bundle_verification_id
            ),
            "final_model_epoch_id": self.final_model_epoch_id,
            "final_proof_id": self.final_proof_id,
            "final_frontier_id": self.final_frontier_id,
            "decision_ids": list(self.decision_ids),
            "barrier_ids": list(self.barrier_ids),
            "executed_round_count": self.executed_round_count,
            "executed_promotion_draw_count": (
                self.executed_promotion_draw_count
            ),
            "registered_round_budget_exactly_replayed": True,
            "registered_draw_budget_exactly_replayed": True,
            "final_proof_still_failed": True,
            "candidate_present": False,
            "infeasibility_proven": False,
            "selected_fq9_terminal_class": TERMINAL_CLASS.value,
            "selected_fq9_terminal_code": TERMINAL_CODE.value,
        }

    @property
    def replay_id(self) -> str:
        return self._replay_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trusted_budget_replay_id": self.replay_id}


def _freeze_budget_replay(
    *,
    bundle: promotion.V075LiveBatchedCausalPromotionBundleV3,
    bundle_verification: (
        promotion.V075LiveBatchedCausalPromotionBundleVerificationV3
    ),
    cap_profile: V075LiveBatchedCausalPromotionCapProfileV3,
) -> V075LiveBatchedCausalPromotionBudgetReplayV3:
    frontier = bundle.final_epoch.proof.failed_frontier
    if (
        bundle.outcome
        is not promotion.V075LiveBatchedCausalPromotionOutcomeV3.PROMOTION_BUDGET_EXHAUSTED
        or bundle.final_epoch.proof.outcome
        is not planning.V075NumericalOutcomeV2.FAILED_FRONTIER
        or frontier is None
        or len(bundle.barriers) != cap_profile.maximum_promotion_rounds
        or any(
            decision.status
            is not promotion.V075LiveBatchedCausalPromotionDecisionStatusV3.AUTHORIZED
            or decision.intent is None
            or decision.intent.accepted_draw_count
            != cap_profile.promotion_draws_per_round
            for decision in bundle.decisions
        )
        or bundle_verification.bundle_id != bundle.bundle_id
        or bundle_verification.outcome is not bundle.outcome
    ):
        _fail("promotion bundle does not prove exact budget exhaustion")
    return V075LiveBatchedCausalPromotionBudgetReplayV3(
        _REPLAY_ISSUER,
        cap_profile.profile_id,
        bundle.bundle_id,
        bundle_verification.verification_id,
        bundle.final_epoch.model_epoch_id,
        bundle.final_epoch.proof.proof_id,
        frontier.frontier_id,
        tuple(item.decision_id for item in bundle.decisions),
        tuple(item.barrier_id for item in bundle.barriers),
        len(bundle.barriers),
        sum(item.intent.accepted_draw_count for item in bundle.decisions if item.intent),
    )


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalBudgetClosedOccurrenceV3:
    _issuer: object = field(repr=False, compare=False)
    promotion_bundle: promotion.V075LiveBatchedCausalPromotionBundleV3 = field(
        repr=False
    )
    promotion_bundle_verification: (
        promotion.V075LiveBatchedCausalPromotionBundleVerificationV3
    )
    cap_profile: V075LiveBatchedCausalPromotionCapProfileV3
    budget_replay: V075LiveBatchedCausalPromotionBudgetReplayV3
    observer_closure: control.V075ControlledBatchJournalClosureV2 = field(
        repr=False
    )
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _CLOSURE_ISSUER
            or type(self.promotion_bundle)
            is not promotion.V075LiveBatchedCausalPromotionBundleV3
            or type(self.promotion_bundle_verification)
            is not promotion.V075LiveBatchedCausalPromotionBundleVerificationV3
            or type(self.cap_profile)
            is not V075LiveBatchedCausalPromotionCapProfileV3
            or type(self.budget_replay)
            is not V075LiveBatchedCausalPromotionBudgetReplayV3
            or type(self.observer_closure)
            is not control.V075ControlledBatchJournalClosureV2
        ):
            _fail("promotion budget closed occurrence is malformed")
        final = self.promotion_bundle.final_epoch
        closed = self.observer_closure
        reconciliation = closed.reconciliation
        if (
            self.promotion_bundle_verification.bundle_id
            != self.promotion_bundle.bundle_id
            or self.budget_replay.promotion_bundle_id
            != self.promotion_bundle.bundle_id
            or self.budget_replay.cap_profile_id != self.cap_profile.profile_id
            or closed.control_closure.final_head_id != final.head_id
            or reconciliation.final_head_id != final.head_id
            or closed.control_closure.receipt_ids != final.append_receipt_ids
            or closed.control_closure.support_freeze_ids
            != final.support_freeze_ids
            or reconciliation.append_count != len(final.controlled_appends)
            or reconciliation.occurrence_id != final.occurrence_id
        ):
            _fail("signed observer closure differs from promotion final epoch")
        object.__setattr__(self, "_closure_id", _hash("closure", self._payload()))

    def _payload(self) -> dict[str, Any]:
        closed = self.observer_closure
        return {
            "schema": "acfqp.v075_live_causal_promotion_budget_closure.v3",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.promotion_bundle.final_epoch.occurrence_id,
            "promotion_bundle_id": self.promotion_bundle.bundle_id,
            "promotion_bundle_verification_id": (
                self.promotion_bundle_verification.verification_id
            ),
            "cap_profile_id": self.cap_profile.profile_id,
            "trusted_budget_replay_id": self.budget_replay.replay_id,
            "final_model_epoch_id": self.promotion_bundle.final_epoch.model_epoch_id,
            "final_proof_id": self.promotion_bundle.final_epoch.proof.proof_id,
            "batch_journal_closure_id": closed.batch_closure.closure_id,
            "control_closure_id": closed.control_closure.control_closure_id,
            "control_reconciliation_id": closed.reconciliation.reconciliation_id,
            "final_head_id": closed.reconciliation.final_head_id,
            "append_count": closed.reconciliation.append_count,
            "total_accepted_draw_count": (
                closed.reconciliation.total_accepted_draw_count
            ),
            "observer_closed_and_exactly_reconciled": True,
            "terminal_scope": TERMINAL_SCOPE,
            "selected_terminal_class": TERMINAL_CLASS.value,
            "selected_terminal_code": TERMINAL_CODE.value,
            "conditional_normalization_target_selected": True,
            "semantic_terminal_verifier_status": (
                SEMANTIC_TERMINAL_VERIFIER_STATUS
            ),
            "terminal_artifact_issued": False,
            "terminal_artifact_issuance_allowed": False,
            "counter_records_issued": 0,
            "work_vector_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def closure_id(self) -> str:
        return self._closure_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "cap_profile": self.cap_profile.to_document(),
            "trusted_budget_replay": self.budget_replay.to_document(),
            "promotion_bundle_verification": (
                self.promotion_bundle_verification.to_document()
            ),
            "observer_closure": self.observer_closure.to_document(),
            "closure_id": self.closure_id,
        }


@dataclass(frozen=True, slots=True)
class V075LiveBatchedCausalBudgetClosureVerificationV3:
    _issuer: object = field(repr=False, compare=False)
    closure_id: str
    promotion_bundle_id: str
    trusted_budget_replay_id: str
    control_reconciliation_id: str
    final_model_epoch_id: str
    terminal_class: TerminalClass
    terminal_code: TerminalCode
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.closure_id, "budget closure verification closure"),
            (self.promotion_bundle_id, "budget closure verification bundle"),
            (self.trusted_budget_replay_id, "budget closure verification replay"),
            (
                self.control_reconciliation_id,
                "budget closure verification reconciliation",
            ),
            (self.final_model_epoch_id, "budget closure verification epoch"),
        ):
            _cid(value, label)
        if (
            self._issuer is not _VERIFICATION_ISSUER
            or self.terminal_class is not TERMINAL_CLASS
            or self.terminal_code is not TERMINAL_CODE
        ):
            _fail("promotion budget closure verification is malformed")
        object.__setattr__(
            self,
            "_verification_id",
            _hash("verification", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_live_causal_promotion_budget_closure_"
                "verification.v3"
            ),
            "schema_version": SCHEMA_VERSION,
            "closure_id": self.closure_id,
            "promotion_bundle_id": self.promotion_bundle_id,
            "trusted_budget_replay_id": self.trusted_budget_replay_id,
            "control_reconciliation_id": self.control_reconciliation_id,
            "final_model_epoch_id": self.final_model_epoch_id,
            "terminal_class": self.terminal_class.value,
            "terminal_code": self.terminal_code.value,
            "promotion_bundle_exactly_replayed": True,
            "registered_budget_exactly_replayed": True,
            "signed_observer_closure_exactly_reconciled": True,
            "terminal_artifact_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        return self._verification_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def _exact_closure_verification(
    closure: V075LiveBatchedCausalBudgetClosedOccurrenceV3,
) -> V075LiveBatchedCausalBudgetClosureVerificationV3:
    return V075LiveBatchedCausalBudgetClosureVerificationV3(
        _VERIFICATION_ISSUER,
        closure.closure_id,
        closure.promotion_bundle.bundle_id,
        closure.budget_replay.replay_id,
        closure.observer_closure.reconciliation.reconciliation_id,
        closure.promotion_bundle.final_epoch.model_epoch_id,
        TERMINAL_CLASS,
        TERMINAL_CODE,
    )


def close_v075_live_batched_causal_budget_exhausted_v3(
    *,
    controller: control.V075ConstructionControlledPrivateObserverV2,
    promotion_bundle: promotion.V075LiveBatchedCausalPromotionBundleV3,
) -> tuple[
    V075LiveBatchedCausalBudgetClosedOccurrenceV3,
    V075LiveBatchedCausalBudgetClosureVerificationV3,
]:
    exact_bundle, bundle_verification = (
        promotion.validate_v075_trusted_owned_batched_causal_promotion_bundle_v3(
            promotion_bundle
        )
    )
    cap_profile = freeze_v075_live_batched_causal_promotion_cap_profile_v3(
        exact_bundle
    )
    budget_replay = _freeze_budget_replay(
        bundle=exact_bundle,
        bundle_verification=bundle_verification,
        cap_profile=cap_profile,
    )
    try:
        closed = controller.close_and_reconcile_v2()
        exact_reconciliation = (
            control.verify_v075_controlled_batch_journal_closure_v2(
                batch_closure=closed.batch_closure,
                heads=closed.heads,
                appends=closed.appends,
                control_closure=closed.control_closure,
                support_freezes=closed.support_freezes,
            )
        )
    except Exception as error:
        raise V075LiveBatchedCausalBudgetClosureV3InvariantViolation(
            "promotion observer closure or exact reconciliation failed"
        ) from error
    if exact_reconciliation.to_document() != closed.reconciliation.to_document():
        _fail("promotion observer reconciliation differs from exact replay")
    closure = V075LiveBatchedCausalBudgetClosedOccurrenceV3(
        _CLOSURE_ISSUER,
        exact_bundle,
        bundle_verification,
        cap_profile,
        budget_replay,
        closed,
    )
    return closure, _exact_closure_verification(closure)


def verify_v075_live_batched_causal_budget_closure_bytes_v3(
    *,
    claimed: V075LiveBatchedCausalBudgetClosedOccurrenceV3,
    claimed_bytes: bytes,
) -> tuple[
    V075LiveBatchedCausalBudgetClosedOccurrenceV3,
    V075LiveBatchedCausalBudgetClosureVerificationV3,
]:
    document = _strict_document(claimed_bytes, "promotion budget closure")
    exact_bundle, bundle_verification = (
        promotion.verify_v075_live_batched_causal_promotion_bundle_bytes_v3(
            claimed=claimed.promotion_bundle,
            claimed_bytes=claimed.promotion_bundle.canonical_bytes,
        )
    )
    cap_profile = freeze_v075_live_batched_causal_promotion_cap_profile_v3(
        exact_bundle
    )
    budget_replay = _freeze_budget_replay(
        bundle=exact_bundle,
        bundle_verification=bundle_verification,
        cap_profile=cap_profile,
    )
    closed = claimed.observer_closure
    reconciliation = control.verify_v075_controlled_batch_journal_closure_v2(
        batch_closure=closed.batch_closure,
        heads=closed.heads,
        appends=closed.appends,
        control_closure=closed.control_closure,
        support_freezes=closed.support_freezes,
    )
    if reconciliation.to_document() != closed.reconciliation.to_document():
        _fail("claimed observer reconciliation differs from exact replay")
    expected = V075LiveBatchedCausalBudgetClosedOccurrenceV3(
        _CLOSURE_ISSUER,
        exact_bundle,
        bundle_verification,
        cap_profile,
        budget_replay,
        closed,
    )
    if set(document) != set(expected.to_document()) or claimed_bytes != (
        expected.canonical_bytes
    ):
        _fail("promotion budget closure differs from exact replay")
    return expected, _exact_closure_verification(expected)


__all__ = (
    "COUNTER_RECORD_ISSUANCE_ALLOWED",
    "OFFICIAL_EXECUTION_ALLOWED",
    "SEMANTIC_TERMINAL_VERIFIER_STATUS",
    "TERMINAL_ARTIFACT_ISSUANCE_ALLOWED",
    "TERMINAL_CLASS",
    "TERMINAL_CODE",
    "V075LiveBatchedCausalBudgetClosedOccurrenceV3",
    "V075LiveBatchedCausalBudgetClosureV3InvariantViolation",
    "V075LiveBatchedCausalBudgetClosureVerificationV3",
    "V075LiveBatchedCausalPromotionBudgetReplayV3",
    "V075LiveBatchedCausalPromotionCapProfileV3",
    "close_v075_live_batched_causal_budget_exhausted_v3",
    "freeze_v075_live_batched_causal_promotion_cap_profile_v3",
    "verify_v075_live_batched_causal_budget_closure_bytes_v3",
)
