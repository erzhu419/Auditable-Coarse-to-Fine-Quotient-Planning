"""Integrated V0-068 observation-discovered partial-support campaign.

This module is deliberately a consumer of the lower-level authorities.  It
does not add a transition interface: physical rows come from the opaque
observer closure, interval models come from the authority-bound bridge, and
exact dynamics are accessed only after an operational audit has frozen or
through the separately charged fallback lane.

The statistical conclusion is conditional on the idealized target-local
uint64 IID authority named by ``observer.STATISTICAL_CLAIM_SCOPE``.  The
deterministic PRNG is only a replay implementation and does not establish
that premise.  This module never upgrades the conditional statement to a
formal exact-IID plan certificate.
"""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from .phase3e_ids import canonical_json_bytes
from . import observation_support_coordinate_refinement_v1 as refinement
from . import observation_support_exact_evaluation_v1 as exact_evaluation
from . import observation_support_graph_acquisition_v1 as acquisition
from . import observation_support_grouped_replay_v1 as grouped_replay
from . import observation_support_graph_model_v1 as graph_model
from . import observation_support_h2_closure_v1 as h2_closure
from . import observation_support_promoted_h2_consumer_v1 as promoted_consumer
from . import partial_support_family_confidence_v1 as family_confidence
from . import partial_support_confidence_v1 as row_confidence
from . import partial_support_expansion_authority_v1 as expansion
from . import partial_support_robust_planner_v1 as robust
from . import transition_tuple_observer_v1 as observer


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "observation_discovered_partial_support_campaign_v0"
REGISTERED_CHECKPOINTS = (2_048, 4_096, 8_192, 16_384)
POSITIVE_CONTEXT_KEYS = (
    "opaque_graph_w5_v0",
    "opaque_graph_k6_v0",
)
NO_COVER_CONTEXT_KEY = "opaque_graph_k6_minus_edge_v0"
REGISTERED_CONTEXT_ORDER = (
    *POSITIVE_CONTEXT_KEYS,
    NO_COVER_CONTEXT_KEY,
)
CONDITIONAL_SCOPE = observer.STATISTICAL_CLAIM_SCOPE
RANDOMNESS_IMPLEMENTATION = observer.REGISTERED_RANDOMNESS_IMPLEMENTATION
FALLBACK_CAP_SEMANTICS = (
    "COMPLETE_SEARCH_POSTHOC_CAP_CLASSIFICATION_NOT_INTERRUPTIBLE_HARD_CAP"
)
OTHER_SEMANTICS = (
    "ONE_EXPLICIT_ADVERSARIAL_ABSORBING_ABORT_FAILURE_DESTINATION"
)


class ObservationSupportCampaignInvariantViolation(ValueError):
    """Raised whenever the integrated identity/claim chain is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
    except Exception as error:  # pragma: no cover - normalized boundary
        raise ObservationSupportCampaignInvariantViolation(str(error)) from error
    return hashlib.sha256(
        f"acfqp:observation-support-campaign:{role}:v1".encode("utf-8")
        + b"\x00"
        + encoded
    ).hexdigest()


def _cid(value: Any, field: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ObservationSupportCampaignInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        )
    return value


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise ObservationSupportCampaignInvariantViolation(
            "campaign rational is not exact"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _registered_context(
    context: observer.PublicGraphContextV1,
) -> observer.PublicGraphContextV1:
    if (
        type(context) is not observer.PublicGraphContextV1
        or context not in observer.registered_public_graph_contexts_v1()
        or context.context_key not in REGISTERED_CONTEXT_ORDER
    ):
        raise ObservationSupportCampaignInvariantViolation(
            "campaign context is not exactly registered"
        )
    return context


def _catalogues(
    closure: h2_closure.ObservationSupportH2ClosureV1,
) -> tuple[observer.LegalActionCatalogueV1, ...]:
    return (closure.root_catalogue, *closure.child_catalogues)


def _threshold(
    context: observer.PublicGraphContextV1,
    bridge: graph_model.ObservationSupportGraphModelBridgeV1,
) -> robust.RobustThresholdProfileV1:
    return robust.RobustThresholdProfileV1(
        context.context_id,
        context.risk_tolerance,
        bridge.reward_ceiling,
        context.normalized_regret_tolerance,
    )


def _row_replay_reference(
    row: acquisition.GraphPartialSupportRowV1,
) -> acquisition.GraphPartialSupportReplayVerificationV1:
    """Materialize the canonical typed replay reference without re-sampling.

    The independent campaign verifier below *does* invoke the full row replay.
    The runner needs only a typed identity when closing the family manifest.
    """

    authority = row.confidence_authority
    epoch = row.support_epoch
    confidence_verification = (
        # This constructor is itself fully identity-bound to the immutable
        # authority.  The family verifier later reconstructs its intervals.
        row_confidence.PartialSupportConfidenceVerificationV1(
            authority_id=authority.authority_id,
            support_epoch_id=epoch.support_epoch_id,
            validation_evidence_id=(
                authority.validation_evidence.validation_evidence_id
            ),
            joint_simplex_id=authority.joint_simplex.joint_simplex_id,
            event_count=epoch.event_count,
            per_event_alpha=epoch.per_event_alpha,
            row_epoch_beta=epoch.row_epoch_beta,
        )
    )
    return acquisition.GraphPartialSupportReplayVerificationV1(
        partial_row_id=row.partial_row_id,
        physical_evidence_id=row.physical_evidence_id,
        confidence_verification_id=confidence_verification.verification_id,
        replayed_support_epoch_index=row.support_epoch_index,
        replayed_observer_draws=row.counters.total_observer_draws,
        replayed_random_word_calls=row.counters.total_random_word_calls,
        replayed_rejections=row.counters.total_rejections,
    )


class CampaignRoute(str, Enum):
    DIRECT = "DIRECT"
    QUOTIENT = "QUOTIENT"


class RouteClosure(str, Enum):
    CONDITIONAL_PLAN_CANDIDATE = "CONDITIONAL_PLAN_CANDIDATE"
    EXACT_FEASIBLE_FALLBACK = "EXACT_FEASIBLE_FALLBACK"
    NONCERTIFICATE = "NONCERTIFICATE"


class OperationalFreezeOutcome(str, Enum):
    ROBUST_PLAN_CERTIFIED = "ROBUST_PLAN_CERTIFIED"
    ROBUST_NO_SOUND_COVER = "ROBUST_NO_SOUND_COVER"


@dataclass(frozen=True, slots=True)
class OperationalRouteFreezeV1:
    """Durable kernel-free result frozen before any exact authority call."""

    context_id: str
    route: CampaignRoute
    checkpoint: int
    bridge_id: str
    model_id: str
    audit_id: str
    threshold_profile_id: str
    terminal_route_proof_id: str
    planning_trace_prefix_id: str
    outcome: OperationalFreezeOutcome
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "operational freeze context"),
            (self.bridge_id, "operational freeze bridge"),
            (self.model_id, "operational freeze model"),
            (self.audit_id, "operational freeze audit"),
            (self.threshold_profile_id, "operational freeze threshold"),
            (self.terminal_route_proof_id, "terminal route proof"),
            (self.planning_trace_prefix_id, "planning trace prefix"),
        ):
            _cid(value, field)
        if (
            type(self.route) is not CampaignRoute
            or self.checkpoint not in REGISTERED_CHECKPOINTS
            or type(self.outcome) is not OperationalFreezeOutcome
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "operational route freeze is not a kernel-free typed result"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_operational_route_freeze.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "route": self.route.value,
            "checkpoint": self.checkpoint,
            "bridge_id": self.bridge_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "threshold_profile_id": self.threshold_profile_id,
            "terminal_route_proof_id": self.terminal_route_proof_id,
            "planning_trace_prefix_id": self.planning_trace_prefix_id,
            "outcome": self.outcome.value,
            "audit_certified": (
                self.outcome
                is OperationalFreezeOutcome.ROBUST_PLAN_CERTIFIED
            ),
            "operational_exact_support_queries": 0,
            "operational_exact_probability_queries": 0,
        }

    @property
    def freeze_id(self) -> str:
        return _content_id("operational_route_freeze", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "freeze_id": self.freeze_id}


@dataclass(frozen=True, slots=True)
class ExactAccessOrderAttestationV1:
    operational_freeze_id: str
    exact_artifact_id: str
    exact_lane: str
    sequence: tuple[str, str] = (
        "OPERATIONAL_ROUTE_FREEZE",
        "EXACT_AUTHORITY_ACCESS",
    )

    def __post_init__(self) -> None:
        _cid(self.operational_freeze_id, "access-order freeze")
        _cid(self.exact_artifact_id, "access-order exact artifact")
        if (
            self.exact_lane
            not in (
                exact_evaluation.EVALUATION_ONLY,
                exact_evaluation.FALLBACK_EXACT,
            )
            or self.sequence
            != (
                "OPERATIONAL_ROUTE_FREEZE",
                "EXACT_AUTHORITY_ACCESS",
            )
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "exact authority was not ordered after operational freeze"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_exact_access_order.v1",
            "schema_version": SCHEMA_VERSION,
            "operational_freeze_id": self.operational_freeze_id,
            "exact_artifact_id": self.exact_artifact_id,
            "exact_lane": self.exact_lane,
            "sequence": list(self.sequence),
            "exact_may_retroactively_change_operational_result": False,
        }

    @property
    def attestation_id(self) -> str:
        return _content_id("exact_access_order", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "attestation_id": self.attestation_id}


@dataclass(frozen=True, slots=True)
class RawPrefixAccountingV1:
    """Exact logical-rebuild and unique-raw-prefix accounting.

    ``rebuild_*`` records actual cumulative-prefix work handed to each
    logical route at every considered checkpoint.  ``unique_*`` is computed
    from the union of immutable raw observation IDs, so checkpoints charge
    only their suffix in the sample-efficiency comparison.
    """

    direct_rebuild_observer_draws: int
    quotient_rebuild_observer_draws: int
    direct_unique_observer_draws: int
    quotient_unique_observer_draws: int
    physical_unique_observer_draws: int
    direct_unique_observation_ids: tuple[str, ...]
    quotient_unique_observation_ids: tuple[str, ...]
    physical_unique_observation_ids: tuple[str, ...]
    actual_closure_build_ids: tuple[str, ...]
    shared_physical_evidence: bool = True

    def __post_init__(self) -> None:
        for value in (
            self.direct_rebuild_observer_draws,
            self.quotient_rebuild_observer_draws,
            self.direct_unique_observer_draws,
            self.quotient_unique_observer_draws,
            self.physical_unique_observer_draws,
        ):
            if type(value) is not int or value < 0:
                raise ObservationSupportCampaignInvariantViolation(
                    "raw-prefix accounting contains an invalid count"
                )
        for values, field in (
            (
                self.direct_unique_observation_ids,
                "direct raw observation",
            ),
            (
                self.quotient_unique_observation_ids,
                "quotient raw observation",
            ),
            (
                self.physical_unique_observation_ids,
                "physical raw observation",
            ),
            (self.actual_closure_build_ids, "actual closure build"),
        ):
            if (
                type(values) is not tuple
                or values != tuple(sorted(set(values)))
                or any(_cid(item, field) != item for item in values)
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    f"{field} IDs are not canonical"
                )
        direct = set(self.direct_unique_observation_ids)
        quotient = set(self.quotient_unique_observation_ids)
        physical = set(self.physical_unique_observation_ids)
        if (
            self.direct_unique_observer_draws != len(direct)
            or self.quotient_unique_observer_draws != len(quotient)
            or self.physical_unique_observer_draws != len(physical)
            or physical != direct | quotient
            or self.direct_rebuild_observer_draws
            < self.direct_unique_observer_draws
            or self.quotient_rebuild_observer_draws
            < self.quotient_unique_observer_draws
            or self.shared_physical_evidence is not True
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "raw-prefix suffix/rebuild reconciliation failed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_raw_prefix_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "direct_rebuild_observer_draws": (
                self.direct_rebuild_observer_draws
            ),
            "quotient_rebuild_observer_draws": (
                self.quotient_rebuild_observer_draws
            ),
            "direct_unique_observer_draws": (
                self.direct_unique_observer_draws
            ),
            "quotient_unique_observer_draws": (
                self.quotient_unique_observer_draws
            ),
            "physical_unique_observer_draws": (
                self.physical_unique_observer_draws
            ),
            "direct_unique_observation_ids": list(
                self.direct_unique_observation_ids
            ),
            "quotient_unique_observation_ids": list(
                self.quotient_unique_observation_ids
            ),
            "physical_unique_observation_ids": list(
                self.physical_unique_observation_ids
            ),
            "actual_closure_build_ids": list(self.actual_closure_build_ids),
            "shared_physical_evidence": True,
            "incremental_rule": (
                "UNION_OF_RAW_OBSERVATION_IDS_NOT_SUM_OF_CUMULATIVE_PREFIXES"
            ),
        }

    @property
    def accounting_id(self) -> str:
        return _content_id("raw_prefix_accounting", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_id": self.accounting_id}


@dataclass(frozen=True, slots=True)
class CheckpointExecutionV1:
    checkpoint: int
    closure: h2_closure.ObservationSupportH2ClosureV1
    bridge: graph_model.ObservationSupportGraphModelBridgeV1
    threshold: robust.RobustThresholdProfileV1
    direct_considered: bool
    direct_audit: robust.RobustPlanAuditV1 | None
    quotient_considered: bool
    quotient_base_audit: robust.RobustPlanAuditV1 | None
    quotient_refinement: (
        refinement.ObservationSupportCoordinateRefinementResultV1 | None
    )
    support_expansion_authorization: (
        expansion.PartialSupportExpansionAuthorizationV1 | None
    )
    promoted_replacement: (
        expansion.PartialSupportPromotedRowReplacementV1 | None
    )
    promoted_consumer_result: (
        promoted_consumer.ObservationSupportPromotedH2ConsumerV1 | None
    )
    quotient_selected_bridge: (
        graph_model.ObservationSupportGraphModelBridgeV1 | None
    )
    quotient_selected_audit: robust.RobustPlanAuditV1 | None

    def __post_init__(self) -> None:
        if (
            type(self.checkpoint) is not int
            or self.checkpoint not in REGISTERED_CHECKPOINTS
            or type(self.closure)
            is not h2_closure.ObservationSupportH2ClosureV1
            or self.closure.validation_checkpoint != self.checkpoint
            or type(self.bridge)
            is not graph_model.ObservationSupportGraphModelBridgeV1
            or self.bridge.context_id != self.closure.context.context_id
            or type(self.threshold) is not robust.RobustThresholdProfileV1
            or self.threshold.context_id != self.closure.context.context_id
            or type(self.direct_considered) is not bool
            or type(self.quotient_considered) is not bool
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "checkpoint authority chain is malformed"
            )
        if self.direct_considered:
            if (
                type(self.direct_audit) is not robust.RobustPlanAuditV1
                or self.direct_audit.model_id
                != self.bridge.direct_model.model_id
                or self.direct_audit.solver_kind
                is not robust.RobustSolverKind.GROUND_DIRECT
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    "direct checkpoint audit is missing or stale"
                )
        elif self.direct_audit is not None:
            raise ObservationSupportCampaignInvariantViolation(
                "stopped direct route was evaluated again"
            )
        if self.quotient_considered:
            if (
                type(self.quotient_base_audit)
                is not robust.RobustPlanAuditV1
                or self.quotient_base_audit.model_id
                != self.bridge.quotient_model.model_id
                or self.quotient_base_audit.solver_kind
                is not robust.RobustSolverKind.QUOTIENT
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    "base quotient audit is missing or stale"
                )
            if self.quotient_base_audit.certified:
                expected_bridge = self.bridge
                expected_audit = self.quotient_base_audit
                if (
                    self.quotient_refinement is not None
                    or self.support_expansion_authorization is not None
                    or self.promoted_replacement is not None
                    or self.promoted_consumer_result is not None
                ):
                    raise ObservationSupportCampaignInvariantViolation(
                        "certified base quotient was unnecessarily refined"
                    )
            else:
                if (
                    type(self.quotient_refinement)
                    is not refinement.ObservationSupportCoordinateRefinementResultV1
                    or self.quotient_refinement.failed_audit_id
                    != self.quotient_base_audit.audit_id
                ):
                    raise ObservationSupportCampaignInvariantViolation(
                        "failed base quotient lacks target-only selector"
                    )
                certified = self.quotient_refinement.certified
                selected = next(
                    (
                        item
                        for item in self.quotient_refinement.candidate_traces
                        if item.certified
                    ),
                    None,
                )
                expected_bridge = (
                    None if selected is None else selected.rebuilt_bridge
                )
                expected_audit = (
                    None if selected is None else selected.robust_audit
                )
                if certified != (selected is not None):
                    raise ObservationSupportCampaignInvariantViolation(
                        "refinement selection result is inconsistent"
                    )
            promotion_items = (
                self.support_expansion_authorization,
                self.promoted_replacement,
                self.promoted_consumer_result,
            )
            if any(item is not None for item in promotion_items):
                if (
                    not all(item is not None for item in promotion_items)
                    or self.closure.context.context_key
                    != "opaque_graph_k6_v0"
                    or self.checkpoint != 8_192
                    or self.support_expansion_authorization.parent_audit_id
                    != self.quotient_base_audit.audit_id
                    or self.promoted_replacement.authorization.authorization_id
                    != self.support_expansion_authorization.authorization_id
                    or self.promoted_consumer_result.replacement_id
                    != self.promoted_replacement.replacement_id
                    or self.promoted_consumer_result.parent_closure_id
                    != self.closure.closure_id
                ):
                    raise ObservationSupportCampaignInvariantViolation(
                        "support promotion transaction is stale or unregistered"
                    )
                if (
                    expected_audit is None
                    and self.promoted_consumer_result.audit.certified
                ):
                    expected_bridge = self.promoted_consumer_result.bridge
                    expected_audit = self.promoted_consumer_result.audit
            if (
                self.quotient_selected_bridge is not expected_bridge
                or self.quotient_selected_audit is not expected_audit
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    "selected quotient bridge/audit is not the first sound one"
                )
        elif any(
            item is not None
            for item in (
                self.quotient_base_audit,
                self.quotient_refinement,
                self.support_expansion_authorization,
                self.promoted_replacement,
                self.promoted_consumer_result,
                self.quotient_selected_bridge,
                self.quotient_selected_audit,
            )
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "stopped quotient route was evaluated again"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_checkpoint_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "checkpoint": self.checkpoint,
            "closure_id": self.closure.closure_id,
            "bridge_id": self.bridge.bridge_id,
            "threshold_profile_id": self.threshold.threshold_profile_id,
            "direct_considered": self.direct_considered,
            "direct_audit_id": (
                None if self.direct_audit is None else self.direct_audit.audit_id
            ),
            "quotient_considered": self.quotient_considered,
            "quotient_base_audit_id": (
                None
                if self.quotient_base_audit is None
                else self.quotient_base_audit.audit_id
            ),
            "quotient_refinement_id": (
                None
                if self.quotient_refinement is None
                else self.quotient_refinement.result_id
            ),
            "support_expansion_authorization_id": (
                None
                if self.support_expansion_authorization is None
                else self.support_expansion_authorization.authorization_id
            ),
            "promoted_replacement_id": (
                None
                if self.promoted_replacement is None
                else self.promoted_replacement.replacement_id
            ),
            "promoted_consumer_id": (
                None
                if self.promoted_consumer_result is None
                else self.promoted_consumer_result.consumer_id
            ),
            "quotient_selected_bridge_id": (
                None
                if self.quotient_selected_bridge is None
                else self.quotient_selected_bridge.bridge_id
            ),
            "quotient_selected_audit_id": (
                None
                if self.quotient_selected_audit is None
                else self.quotient_selected_audit.audit_id
            ),
            "operational_exact_support_queries": 0,
            "operational_exact_probability_queries": 0,
            "other_semantics": OTHER_SEMANTICS,
        }

    @property
    def execution_id(self) -> str:
        return _content_id("checkpoint_execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}


@dataclass(frozen=True, slots=True)
class RouteResultV1:
    context_id: str
    route: CampaignRoute
    closure: RouteClosure
    first_certificate_checkpoint: int | None
    bridge: graph_model.ObservationSupportGraphModelBridgeV1 | None
    audit: robust.RobustPlanAuditV1 | None
    operational_freeze: OperationalRouteFreezeV1 | None
    exact_access_order: ExactAccessOrderAttestationV1 | None
    exact_lift: (
        exact_evaluation.ObservationSupportExactLiftEvaluationV1 | None
    )
    exact_fallback: (
        exact_evaluation.ObservationSupportExactFallbackResultV1 | None
    )

    def __post_init__(self) -> None:
        _cid(self.context_id, "route context")
        if (
            type(self.route) is not CampaignRoute
            or type(self.closure) is not RouteClosure
            or (
                self.first_certificate_checkpoint is not None
                and self.first_certificate_checkpoint
                not in REGISTERED_CHECKPOINTS
            )
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "route result classification is invalid"
            )
        if self.closure is RouteClosure.CONDITIONAL_PLAN_CANDIDATE:
            if (
                self.first_certificate_checkpoint is None
                or type(self.bridge)
                is not graph_model.ObservationSupportGraphModelBridgeV1
                or type(self.audit) is not robust.RobustPlanAuditV1
                or not self.audit.certified
                or type(self.operational_freeze)
                is not OperationalRouteFreezeV1
                or self.operational_freeze.context_id != self.context_id
                or self.operational_freeze.route is not self.route
                or self.operational_freeze.checkpoint
                != self.first_certificate_checkpoint
                or self.operational_freeze.bridge_id != self.bridge.bridge_id
                or self.operational_freeze.model_id != self.audit.model_id
                or self.operational_freeze.audit_id != self.audit.audit_id
                or self.operational_freeze.threshold_profile_id
                != self.audit.threshold_profile_id
                or self.operational_freeze.outcome
                is not OperationalFreezeOutcome.ROBUST_PLAN_CERTIFIED
                or type(self.exact_access_order)
                is not ExactAccessOrderAttestationV1
                or self.exact_access_order.operational_freeze_id
                != self.operational_freeze.freeze_id
                or self.exact_access_order.exact_lane
                != exact_evaluation.EVALUATION_ONLY
                or type(self.exact_lift)
                is not exact_evaluation.ObservationSupportExactLiftEvaluationV1
                or self.exact_lift.audit_id != self.audit.audit_id
                or self.exact_lift.bridge_id != self.bridge.bridge_id
                or self.exact_lift.prerequisite_operational_freeze_id
                != self.operational_freeze.freeze_id
                or self.exact_access_order.exact_artifact_id
                != self.exact_lift.evaluation_id
                or self.exact_fallback is not None
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    "conditional route lacks its frozen audit/exact lift"
                )
        elif self.closure is RouteClosure.EXACT_FEASIBLE_FALLBACK:
            if (
                self.first_certificate_checkpoint is not None
                or self.bridge is not None
                or self.audit is not None
                or type(self.operational_freeze)
                is not OperationalRouteFreezeV1
                or self.operational_freeze.context_id != self.context_id
                or self.operational_freeze.route is not self.route
                or self.operational_freeze.outcome
                is not OperationalFreezeOutcome.ROBUST_NO_SOUND_COVER
                or type(self.exact_access_order)
                is not ExactAccessOrderAttestationV1
                or self.exact_access_order.operational_freeze_id
                != self.operational_freeze.freeze_id
                or self.exact_access_order.exact_lane
                != exact_evaluation.FALLBACK_EXACT
                or self.exact_lift is not None
                or type(self.exact_fallback)
                is not exact_evaluation.ObservationSupportExactFallbackResultV1
                or not self.exact_fallback.feasible_plan_certified
                or self.exact_fallback.infeasibility_certified
                or self.exact_fallback.prerequisite_operational_freeze_id
                != self.operational_freeze.freeze_id
                or self.exact_access_order.exact_artifact_id
                != self.exact_fallback.fallback_result_id
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    "exact fallback route is not a feasible-only closure"
                )
        else:
            if (
                self.first_certificate_checkpoint is not None
                or self.bridge is not None
                or self.audit is not None
                or type(self.operational_freeze)
                is not OperationalRouteFreezeV1
                or self.operational_freeze.outcome
                is not OperationalFreezeOutcome.ROBUST_NO_SOUND_COVER
                or self.exact_lift is not None
                or type(self.exact_access_order)
                is not ExactAccessOrderAttestationV1
                or self.exact_access_order.operational_freeze_id
                != self.operational_freeze.freeze_id
                or self.exact_access_order.exact_lane
                != exact_evaluation.FALLBACK_EXACT
                or (
                    self.exact_fallback is not None
                    and not self.exact_fallback.cap_exhausted
                )
                or (
                    self.exact_fallback is not None
                    and self.exact_access_order.exact_artifact_id
                    != self.exact_fallback.fallback_result_id
                )
                or (
                    self.exact_fallback is not None
                    and self.exact_fallback
                    .prerequisite_operational_freeze_id
                    != self.operational_freeze.freeze_id
                )
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    "noncertificate route contains invalid certificate material"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_route_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "route": self.route.value,
            "closure": self.closure.value,
            "first_certificate_checkpoint": (
                self.first_certificate_checkpoint
            ),
            "bridge_id": (
                None if self.bridge is None else self.bridge.bridge_id
            ),
            "audit_id": None if self.audit is None else self.audit.audit_id,
            "operational_freeze_id": (
                None
                if self.operational_freeze is None
                else self.operational_freeze.freeze_id
            ),
            "exact_access_order_attestation_id": (
                None
                if self.exact_access_order is None
                else self.exact_access_order.attestation_id
            ),
            "exact_lift_evaluation_id": (
                None
                if self.exact_lift is None
                else self.exact_lift.evaluation_id
            ),
            "exact_fallback_result_id": (
                None
                if self.exact_fallback is None
                else self.exact_fallback.fallback_result_id
            ),
            "statistical_claim_scope": CONDITIONAL_SCOPE,
            "randomness_implementation": RANDOMNESS_IMPLEMENTATION,
            "formal_exact_iid_plan_certificate": False,
            "fallback_cap_semantics": (
                FALLBACK_CAP_SEMANTICS
                if self.exact_fallback is not None
                else None
            ),
        }

    @property
    def route_result_id(self) -> str:
        return _content_id("route_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "route_result_id": self.route_result_id}


@dataclass(frozen=True, slots=True)
class ContextCampaignResultV1:
    context: observer.PublicGraphContextV1
    executions: tuple[CheckpointExecutionV1, ...]
    other_escape_handler: graph_model.GraphOtherOutcomeEscapeHandlerV1
    direct_result: RouteResultV1
    quotient_result: RouteResultV1
    accounting: RawPrefixAccountingV1

    def __post_init__(self) -> None:
        context = _registered_context(self.context)
        if (
            type(self.executions) is not tuple
            or not self.executions
            or any(
                type(item) is not CheckpointExecutionV1
                for item in self.executions
            )
            or type(self.other_escape_handler)
            is not graph_model.GraphOtherOutcomeEscapeHandlerV1
            or self.other_escape_handler.context_id != context.context_id
            or any(
                item.bridge.other_escape_handler.handler_id
                != self.other_escape_handler.handler_id
                for item in self.executions
            )
            or tuple(item.checkpoint for item in self.executions)
            != REGISTERED_CHECKPOINTS[: len(self.executions)]
            or any(
                item.closure.context.context_id != context.context_id
                for item in self.executions
            )
            or type(self.direct_result) is not RouteResultV1
            or type(self.quotient_result) is not RouteResultV1
            or self.direct_result.route is not CampaignRoute.DIRECT
            or self.quotient_result.route is not CampaignRoute.QUOTIENT
            or self.direct_result.context_id != context.context_id
            or self.quotient_result.context_id != context.context_id
            or type(self.accounting) is not RawPrefixAccountingV1
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "context campaign result is not chronological or bound"
            )
        direct_certified = [
            item
            for item in self.executions
            if item.direct_audit is not None and item.direct_audit.certified
        ]
        quotient_certified = [
            item
            for item in self.executions
            if item.quotient_selected_audit is not None
            and item.quotient_selected_audit.certified
        ]
        for candidates, result in (
            (direct_certified, self.direct_result),
            (quotient_certified, self.quotient_result),
        ):
            if result.closure is RouteClosure.CONDITIONAL_PLAN_CANDIDATE:
                if (
                    not candidates
                    or result.first_certificate_checkpoint
                    != candidates[0].checkpoint
                    or len(candidates) != 1
                ):
                    raise ObservationSupportCampaignInvariantViolation(
                        "route did not stop at its first certificate"
                    )
        for route, result in (
            (CampaignRoute.DIRECT, self.direct_result),
            (CampaignRoute.QUOTIENT, self.quotient_result),
        ):
            if (
                result.operational_freeze is None
                or result.operational_freeze.planning_trace_prefix_id
                != _route_trace_prefix_id(self.executions, route)
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    "operational freeze omits its complete route chronology"
                )
        if (
            self.direct_result.operational_freeze.terminal_route_proof_id
            != self.direct_result.operational_freeze.audit_id
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "direct terminal proof is not its final robust audit"
            )
        if (
            self.quotient_result.closure
            is not RouteClosure.CONDITIONAL_PLAN_CANDIDATE
        ):
            last = next(
                item
                for item in reversed(self.executions)
                if item.quotient_considered
            )
            expected_terminal = (
                last.quotient_refinement.result_id
                if last.quotient_refinement is not None
                else last.quotient_base_audit.audit_id
            )
            if (
                self.quotient_result.operational_freeze
                .terminal_route_proof_id
                != expected_terminal
            ):
                raise ObservationSupportCampaignInvariantViolation(
                    "fallback freeze does not bind final no-cover authority"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_context_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context.context_id,
            "execution_ids": [item.execution_id for item in self.executions],
            "other_escape_handler_id": self.other_escape_handler.handler_id,
            "direct_result_id": self.direct_result.route_result_id,
            "quotient_result_id": self.quotient_result.route_result_id,
            "accounting_id": self.accounting.accounting_id,
        }

    @property
    def context_result_id(self) -> str:
        return _content_id("context_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_result_id": self.context_result_id}


@dataclass(frozen=True, slots=True)
class ConditionalTerminalEnvelopeV1:
    context_result_id: str
    route_result_id: str
    family_authority_id: str
    route: CampaignRoute
    terminal_class: str
    conditional_statistical_scope: str = CONDITIONAL_SCOPE
    randomness_implementation: str = RANDOMNESS_IMPLEMENTATION
    exact_iid_implementation_claimed: bool = False
    formal_exact_iid_plan_certificate: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_result_id, "terminal context result"),
            (self.route_result_id, "terminal route result"),
            (self.family_authority_id, "terminal family authority"),
        ):
            _cid(value, field)
        if (
            type(self.route) is not CampaignRoute
            or self.terminal_class
            not in (
                "CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE",
                "EXACT_FEASIBLE_FALLBACK",
                "NONCERTIFICATE",
            )
            or self.conditional_statistical_scope != CONDITIONAL_SCOPE
            or self.randomness_implementation != RANDOMNESS_IMPLEMENTATION
            or self.exact_iid_implementation_claimed is not False
            or self.formal_exact_iid_plan_certificate is not False
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "terminal envelope overstates its statistical authority"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_terminal_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "context_result_id": self.context_result_id,
            "route_result_id": self.route_result_id,
            "family_authority_id": self.family_authority_id,
            "route": self.route.value,
            "terminal_class": self.terminal_class,
            "conditional_statistical_scope": (
                self.conditional_statistical_scope
            ),
            "randomness_implementation": self.randomness_implementation,
            "exact_iid_implementation_claimed": False,
            "formal_exact_iid_plan_certificate": False,
        }

    @property
    def envelope_id(self) -> str:
        return _content_id("terminal_envelope", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "envelope_id": self.envelope_id}


@dataclass(frozen=True, slots=True)
class CampaignCounterSummaryV1:
    physical_unique_observer_draws: int
    physical_unique_random_word_calls: int
    physical_unique_rejections: int
    logical_direct_rebuild_observer_draws: int
    logical_quotient_rebuild_observer_draws: int
    unique_support_epoch_count: int
    promoted_support_epoch_count: int
    promoted_outcome_count: int
    base_model_build_count: int
    coordinate_candidate_model_build_count: int
    expansion_candidate_model_build_count: int
    promoted_model_build_count: int
    direct_audit_count: int
    base_quotient_audit_count: int
    coordinate_candidate_audit_count: int
    expansion_causal_counterfactual_audit_count: int
    promoted_replan_audit_count: int
    fallback_exact_state_action_rows: int
    standalone_exact_state_action_rows: int
    operational_exact_support_queries: int = 0
    operational_exact_probability_queries: int = 0

    def __post_init__(self) -> None:
        values = tuple(
            getattr(self, field) for field in self.__dataclass_fields__
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.physical_unique_random_word_calls
            != (
                self.physical_unique_observer_draws
                + self.physical_unique_rejections
            )
            or self.base_model_build_count <= 0
            or self.direct_audit_count <= 0
            or self.base_quotient_audit_count <= 0
            or self.operational_exact_support_queries != 0
            or self.operational_exact_probability_queries != 0
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "campaign counter summary does not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_campaign_counters.v1",
            "schema_version": SCHEMA_VERSION,
            **{
                field: getattr(self, field)
                for field in self.__dataclass_fields__
            },
            "sample_advantage_metric": (
                "UNIQUE_RAW_OBSERVATION_PREFIX_CALLS_ONLY"
            ),
            "counter_completeness_claimed": False,
        }

    @property
    def counters_id(self) -> str:
        return _content_id("campaign_counters", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counters_id": self.counters_id}


@dataclass(frozen=True, slots=True)
class VerifiedArtifactRoleBindingV1:
    artifact_role: str
    artifact_id: str
    semantic_verification_id: str

    def __post_init__(self) -> None:
        if type(self.artifact_role) is not str or not self.artifact_role:
            raise ObservationSupportCampaignInvariantViolation(
                "verified artifact role is empty"
            )
        _cid(self.artifact_id, "verified role artifact")
        _cid(self.semantic_verification_id, "semantic verification")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_verified_artifact_role.v1",
            "schema_version": SCHEMA_VERSION,
            "artifact_role": self.artifact_role,
            "artifact_id": self.artifact_id,
            "semantic_verification_id": self.semantic_verification_id,
        }

    @property
    def binding_id(self) -> str:
        return _content_id("verified_role_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class DurableVerifiedRoleManifestV1:
    campaign_id: str
    bindings: tuple[VerifiedArtifactRoleBindingV1, ...]
    complete_same_implementation_bundle: bool = True

    def __post_init__(self) -> None:
        _cid(self.campaign_id, "role manifest campaign")
        required_roles = {
            "REGISTERED_OTHER_ABSORBING_ABORT_HANDLER",
            "RAW_PARTIAL_SUPPORT_ROW_REPLAY",
            "OBSERVATION_ONLY_H2_CLOSURE",
            "AUTHORITY_BOUND_BASE_MODEL_BRIDGE",
            "DIRECT_ROBUST_AUDIT",
            "BASE_QUOTIENT_ROBUST_AUDIT",
            "TARGET_OBSERVATION_ONLY_COORDINATE_REFINEMENT",
            "CAUSAL_SUPPORT_EXPANSION_AUTHORIZATION",
            "FRESH_PROMOTED_ROW_REPLACEMENT",
            "PROMOTED_MIXED_EPOCH_CLOSURE_REPLAN",
            "FAILED_PROMOTED_ROBUST_AUDIT",
            "CLOSED_ALL_CONSIDERED_FAMILY_CONFIDENCE",
            "PRE_EXACT_OPERATIONAL_ROUTE_FREEZE",
            "EXACT_ACCESS_ORDER_ATTESTATION",
            "STANDALONE_EXACT_LIFT_EVALUATION",
            "COMPLETE_SEARCH_POSTHOC_CAP_EXACT_FALLBACK",
            "COMPLETE_CAMPAIGN_SAME_IMPLEMENTATION_REPLAY",
        }
        if (
            type(self.bindings) is not tuple
            or not self.bindings
            or any(
                type(item) is not VerifiedArtifactRoleBindingV1
                for item in self.bindings
            )
            or tuple(item.binding_id for item in self.bindings)
            != tuple(sorted({item.binding_id for item in self.bindings}))
            or len(
                {
                    (item.artifact_role, item.artifact_id)
                    for item in self.bindings
                }
            )
            != len(self.bindings)
            or len({item.artifact_id for item in self.bindings})
            != len(self.bindings)
            or not required_roles.issubset(
                {item.artifact_role for item in self.bindings}
            )
            or self.complete_same_implementation_bundle is not True
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "durable verified role manifest is incomplete or duplicated"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_verified_role_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "binding_ids": [item.binding_id for item in self.bindings],
            "complete_same_implementation_bundle": True,
            "independent_implementation_claimed": False,
        }

    @property
    def manifest_id(self) -> str:
        return _content_id("verified_role_manifest", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "bindings": [item.to_document() for item in self.bindings],
            "manifest_id": self.manifest_id,
        }


@dataclass(frozen=True, slots=True)
class ObservationSupportCampaignV1:
    context_results: tuple[ContextCampaignResultV1, ...]
    family_manifest: family_confidence.PlanningRowEpochManifestV1
    family_authority: (
        family_confidence.PartialSupportFamilyConfidenceAuthorityV1
    )
    terminal_envelopes: tuple[ConditionalTerminalEnvelopeV1, ...]
    counters: CampaignCounterSummaryV1
    construction_gate_passed: bool
    matched_observation_advantage: bool
    aggregate_direct_unique_observer_draws: int
    aggregate_quotient_unique_observer_draws: int
    physical_unique_observer_draws: int
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None
    WORKLOAD_ECONOMICS_GATE_NOT_RUN: bool = True
    COUNTER_COMPLETENESS_GATE_NOT_RUN: bool = True
    support_expansion_executed: bool = True
    support_expansion_certified: bool = False
    exact_iid_implementation_claimed: bool = False
    formal_exact_iid_plan_certificate: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.context_results) is not tuple
            or tuple(
                item.context.context_key for item in self.context_results
            )
            != REGISTERED_CONTEXT_ORDER
            or any(
                type(item) is not ContextCampaignResultV1
                for item in self.context_results
            )
            or type(self.family_manifest)
            is not family_confidence.PlanningRowEpochManifestV1
            or type(self.family_authority)
            is not family_confidence.PartialSupportFamilyConfidenceAuthorityV1
            or self.family_authority.manifest.manifest_id
            != self.family_manifest.manifest_id
            or type(self.terminal_envelopes) is not tuple
            or len(self.terminal_envelopes)
            != 2 * len(self.context_results)
            or any(
                type(item) is not ConditionalTerminalEnvelopeV1
                for item in self.terminal_envelopes
            )
            or type(self.counters) is not CampaignCounterSummaryV1
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "campaign authority graph is incomplete"
            )
        direct = sum(
            item.accounting.direct_unique_observer_draws
            for item in self.context_results
        )
        quotient = sum(
            item.accounting.quotient_unique_observer_draws
            for item in self.context_results
        )
        physical_ids = {
            observation_id
            for item in self.context_results
            for observation_id in (
                item.accounting.physical_unique_observation_ids
            )
        }
        positives = tuple(
            item
            for item in self.context_results
            if item.context.context_key in POSITIVE_CONTEXT_KEYS
        )
        negative = next(
            item
            for item in self.context_results
            if item.context.context_key == NO_COVER_CONTEXT_KEY
        )
        promotions = tuple(
            execution.promoted_consumer_result
            for item in self.context_results
            for execution in item.executions
            if execution.promoted_consumer_result is not None
        )
        expansion_candidate_count = sum(
            len(execution.support_expansion_authorization.candidate_evidence)
            for item in self.context_results
            for execution in item.executions
            if execution.support_expansion_authorization is not None
        )
        expected_construction = (
            all(
                item.direct_result.closure
                is RouteClosure.CONDITIONAL_PLAN_CANDIDATE
                and item.quotient_result.closure
                is RouteClosure.CONDITIONAL_PLAN_CANDIDATE
                for item in positives
            )
            and negative.quotient_result.closure
            is RouteClosure.EXACT_FEASIBLE_FALLBACK
            and negative.direct_result.closure
            is RouteClosure.EXACT_FEASIBLE_FALLBACK
            and self.family_authority.formal_exact_iid_plan_certificate
            is False
        )
        expected_advantage = (
            expected_construction
            and quotient < direct
            and all(
                item.accounting.quotient_unique_observer_draws
                <= item.accounting.direct_unique_observer_draws
                for item in positives
            )
        )
        if (
            self.construction_gate_passed is not expected_construction
            or self.matched_observation_advantage is not expected_advantage
            or self.aggregate_direct_unique_observer_draws != direct
            or self.aggregate_quotient_unique_observer_draws != quotient
            or self.physical_unique_observer_draws != len(physical_ids)
            or self.counters.physical_unique_observer_draws
            != self.physical_unique_observer_draws
            or self.counters.logical_direct_rebuild_observer_draws
            != sum(
                item.accounting.direct_rebuild_observer_draws
                for item in self.context_results
            )
            or self.counters.logical_quotient_rebuild_observer_draws
            != sum(
                item.accounting.quotient_rebuild_observer_draws
                for item in self.context_results
            )
            or self.counters.promoted_support_epoch_count != 1
            or self.counters.promoted_outcome_count <= 0
            or self.counters.expansion_candidate_model_build_count
            != expansion_candidate_count
            or self.counters.expansion_causal_counterfactual_audit_count
            != expansion_candidate_count
            or len(promotions) != 1
            or promotions[0].audit.certified
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
            or self.WORKLOAD_ECONOMICS_GATE_NOT_RUN is not True
            or self.COUNTER_COMPLETENESS_GATE_NOT_RUN is not True
            or self.support_expansion_executed is not True
            or self.support_expansion_certified is not False
            or self.exact_iid_implementation_claimed is not False
            or self.formal_exact_iid_plan_certificate is not False
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "campaign gate/lock conclusion is not mechanically derived"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_result_ids": [
                item.context_result_id for item in self.context_results
            ],
            "family_manifest_id": self.family_manifest.manifest_id,
            "family_authority_id": self.family_authority.authority_id,
            "terminal_envelope_ids": [
                item.envelope_id for item in self.terminal_envelopes
            ],
            "counters_id": self.counters.counters_id,
            "construction_gate_passed": self.construction_gate_passed,
            "matched_observation_advantage": (
                self.matched_observation_advantage
            ),
            "matched_observation_advantage_metric": (
                "UNIQUE_RAW_OBSERVATION_PREFIX_CALLS_ONLY"
            ),
            "aggregate_direct_unique_observer_draws": (
                self.aggregate_direct_unique_observer_draws
            ),
            "aggregate_quotient_unique_observer_draws": (
                self.aggregate_quotient_unique_observer_draws
            ),
            "physical_unique_observer_draws": (
                self.physical_unique_observer_draws
            ),
            "randomness_implementation": RANDOMNESS_IMPLEMENTATION,
            "conditional_statistical_scope": CONDITIONAL_SCOPE,
            "exact_iid_implementation_claimed": False,
            "formal_exact_iid_plan_certificate": False,
            "exact_access_order_source_ordered": True,
            "exact_access_order_capability_enforced": False,
            "exact_artifacts_natively_bind_operational_freeze_id": False,
            "other_escape_handler_campaign_bound": True,
            "other_escape_handler_natively_bound_by_exact_evaluator": False,
            "family_cap_checked_before_exact_evaluation": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "WORKLOAD_ECONOMICS_GATE_NOT_RUN": True,
            "COUNTER_COMPLETENESS_GATE_NOT_RUN": True,
            "support_expansion_gate_status": (
                "EXECUTED_FAILED_REPLAN_CONTINUED_TO_NEXT_CHECKPOINT"
            ),
            "support_expansion_executed": True,
            "support_expansion_certified": False,
        }

    @property
    def campaign_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_id": self.campaign_id}


@dataclass(frozen=True, slots=True)
class ObservationSupportCampaignFamilyCapExhaustedV1:
    context_results: tuple[ContextCampaignResultV1, ...]
    family_manifest: family_confidence.PlanningRowEpochManifestV1
    family_cap: family_confidence.PartialSupportFamilyCapExhaustedV1
    construction_gate_passed: bool = False
    matched_observation_advantage: bool = False
    terminal_class: str = "ATTEMPT_CLOSURE_NONCERTIFICATE"
    terminal_code: str = "FAMILY_ROW_EPOCH_CAP_EXHAUSTED"
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None

    def __post_init__(self) -> None:
        if (
            type(self.context_results) is not tuple
            or tuple(item.context.context_key for item in self.context_results)
            != REGISTERED_CONTEXT_ORDER
            or type(self.family_manifest)
            is not family_confidence.PlanningRowEpochManifestV1
            or type(self.family_cap)
            is not family_confidence.PartialSupportFamilyCapExhaustedV1
            or self.family_cap.manifest.manifest_id
            != self.family_manifest.manifest_id
            or self.construction_gate_passed is not False
            or self.matched_observation_advantage is not False
            or self.terminal_class
            != "ATTEMPT_CLOSURE_NONCERTIFICATE"
            or self.terminal_code != "FAMILY_ROW_EPOCH_CAP_EXHAUSTED"
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "family cap exhaustion was not a typed noncertificate closure"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.observation_support_campaign_family_cap_exhausted.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_operational_trace_ids": [
                _context_operational_trace_id(item)
                for item in self.context_results
            ],
            "family_manifest_id": self.family_manifest.manifest_id,
            "family_cap_closure_id": self.family_cap.closure_id,
            "construction_gate_passed": False,
            "matched_observation_advantage": False,
            "terminal_class": self.terminal_class,
            "terminal_code": self.terminal_code,
            "infeasibility_certified": False,
            "family_cap_checked_before_exact_evaluation": False,
            "official_execution_allowed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
        }

    @property
    def closure_id(self) -> str:
        return _content_id("campaign_family_cap_exhausted", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "closure_id": self.closure_id}


def _observation_ids(
    rows: Iterable[acquisition.GraphPartialSupportRowV1],
) -> set[str]:
    return {
        observation_id
        for row in rows
        for observation_id in (
            *row.initial_discovery_observation_ids,
            *row.prior_validation_observation_ids,
            *row.current_validation_observation_ids,
        )
    }


def _selected_refinement(
    result: refinement.ObservationSupportCoordinateRefinementResultV1,
) -> tuple[
    graph_model.ObservationSupportGraphModelBridgeV1 | None,
    robust.RobustPlanAuditV1 | None,
]:
    selected = next(
        (item for item in result.candidate_traces if item.certified),
        None,
    )
    return (
        None if selected is None else selected.rebuilt_bridge,
        None if selected is None else selected.robust_audit,
    )


def _route_trace_prefix_id(
    executions: Iterable[CheckpointExecutionV1],
    route: CampaignRoute,
) -> str:
    values = tuple(executions)
    return _content_id(
        "route_trace_prefix",
        {
            "schema": "acfqp.observation_support_route_trace_prefix.v1",
            "schema_version": SCHEMA_VERSION,
            "route": route.value,
            "execution_ids": [
                item.execution_id
                for item in values
                if (
                    item.direct_considered
                    if route is CampaignRoute.DIRECT
                    else item.quotient_considered
                )
            ],
        },
    )


def run_observation_support_context_v1(
    context: observer.PublicGraphContextV1,
    *,
    max_workers: int = 1,
) -> ContextCampaignResultV1:
    """Run one context through chronological matched route checkpoints."""

    registered = _registered_context(context)
    direct_open = True
    quotient_open = True
    direct_terminal: tuple[
        int,
        graph_model.ObservationSupportGraphModelBridgeV1,
        robust.RobustPlanAuditV1,
    ] | None = None
    quotient_terminal: tuple[
        int,
        graph_model.ObservationSupportGraphModelBridgeV1,
        robust.RobustPlanAuditV1,
    ] | None = None
    executions: list[CheckpointExecutionV1] = []
    direct_ids: set[str] = set()
    quotient_ids: set[str] = set()
    direct_rebuild = 0
    quotient_rebuild = 0
    closure_ids: set[str] = set()

    for checkpoint in REGISTERED_CHECKPOINTS:
        if not direct_open and not quotient_open:
            break
        closure = h2_closure.acquire_observation_support_h2_closure_v1(
            registered,
            checkpoint,
            max_workers=max_workers,
        )
        closure_ids.add(closure.closure_id)
        bridge = graph_model.build_observation_support_graph_models_v1(
            context=registered,
            root_catalogue=closure.root_catalogue,
            catalogues=_catalogues(closure),
            partial_rows=closure.all_rows,
        )
        graph_model.verify_observation_support_graph_models_v1(
            context=registered,
            root_catalogue=closure.root_catalogue,
            catalogues=_catalogues(closure),
            partial_rows=closure.all_rows,
            bridge=bridge,
        )
        threshold = _threshold(registered, bridge)

        direct_audit = None
        if direct_open:
            direct_rebuild += closure.counters.total_observer_draws
            direct_ids.update(_observation_ids(closure.all_rows))
            direct_audit = robust.solve_ground_direct_robust_h2_v1(
                bridge.direct_model,
                threshold,
            )
            robust.verify_robust_plan_audit_v1(
                bridge.direct_model,
                threshold,
                direct_audit,
            )
            if direct_audit.certified:
                direct_terminal = (checkpoint, bridge, direct_audit)
                direct_open = False

        quotient_base_audit = None
        quotient_refinement = None
        support_expansion_authorization = None
        promoted_replacement = None
        promoted_consumer_result = None
        quotient_bridge = None
        quotient_audit = None
        if quotient_open:
            quotient_rebuild += closure.counters.total_observer_draws
            quotient_ids.update(_observation_ids(closure.all_rows))
            quotient_base_audit = robust.solve_quotient_robust_h2_v1(
                bridge.quotient_model,
                threshold,
            )
            robust.verify_robust_plan_audit_v1(
                bridge.quotient_model,
                threshold,
                quotient_base_audit,
            )
            if quotient_base_audit.certified:
                quotient_bridge = bridge
                quotient_audit = quotient_base_audit
            else:
                quotient_refinement = (
                    refinement.refine_observation_support_coordinates_v1(
                        context=registered,
                        closure=closure,
                        base_bridge=bridge,
                        failed_audit=quotient_base_audit,
                    )
                )
                refinement.verify_observation_support_coordinate_refinement_v1(
                    context=registered,
                    closure=closure,
                    base_bridge=bridge,
                    failed_audit=quotient_base_audit,
                    claimed=quotient_refinement,
                )
                quotient_bridge, quotient_audit = _selected_refinement(
                    quotient_refinement
                )
            if (
                quotient_audit is None
                and registered.context_key == "opaque_graph_k6_v0"
                and checkpoint == 8_192
            ):
                support_expansion_authorization = (
                    expansion.authorize_partial_support_expansion_v1(
                        bridge=bridge,
                        audit=quotient_base_audit,
                        threshold=threshold,
                        partial_rows=closure.all_rows,
                        checkpoint_draw_count=2_048,
                    )
                )
                promoted_replacement = (
                    expansion.promote_authorized_partial_support_row_v1(
                        bridge=bridge,
                        audit=quotient_base_audit,
                        threshold=threshold,
                        partial_rows=closure.all_rows,
                        authorization=support_expansion_authorization,
                    )
                )
                promoted_consumer_result = (
                    promoted_consumer
                    .consume_partial_support_promoted_row_replacement_v1(
                        context=registered,
                        parent_closure=closure,
                        parent_bridge=bridge,
                        parent_audit=quotient_base_audit,
                        threshold=threshold,
                        replacement=promoted_replacement,
                        new_child_validation_checkpoint=8_192,
                        max_workers=max_workers,
                    )
                )
                quotient_rebuild += (
                    promoted_consumer_result.counters
                    .incremental_observer_draws
                )
                quotient_ids.update(
                    _observation_ids(
                        promoted_consumer_result.promoted_closure.all_rows
                    )
                )
                closure_ids.add(
                    promoted_consumer_result.promoted_closure.closure_id
                )
                if promoted_consumer_result.audit.certified:
                    quotient_bridge = promoted_consumer_result.bridge
                    quotient_audit = promoted_consumer_result.audit
            if quotient_audit is not None and quotient_audit.certified:
                quotient_terminal = (
                    checkpoint,
                    quotient_bridge,
                    quotient_audit,
                )
                quotient_open = False

        executions.append(
            CheckpointExecutionV1(
                checkpoint=checkpoint,
                closure=closure,
                bridge=bridge,
                threshold=threshold,
                direct_considered=direct_audit is not None,
                direct_audit=direct_audit,
                quotient_considered=quotient_base_audit is not None,
                quotient_base_audit=quotient_base_audit,
                quotient_refinement=quotient_refinement,
                support_expansion_authorization=(
                    support_expansion_authorization
                ),
                promoted_replacement=promoted_replacement,
                promoted_consumer_result=promoted_consumer_result,
                quotient_selected_bridge=quotient_bridge,
                quotient_selected_audit=quotient_audit,
            )
        )

    if direct_terminal is not None:
        checkpoint, bridge, audit = direct_terminal
        freeze = OperationalRouteFreezeV1(
            registered.context_id,
            CampaignRoute.DIRECT,
            checkpoint,
            bridge.bridge_id,
            audit.model_id,
            audit.audit_id,
            audit.threshold_profile_id,
            audit.audit_id,
            _route_trace_prefix_id(
                executions,
                CampaignRoute.DIRECT,
            ),
            OperationalFreezeOutcome.ROBUST_PLAN_CERTIFIED,
        )
        # Materialize the durable operational identity before the first
        # evaluation-only hidden-law call.
        _ = freeze.freeze_id
        lift = exact_evaluation.evaluate_observation_support_exact_lift_v1(
            registered,
            bridge,
            audit,
            prerequisite_operational_freeze_id=freeze.freeze_id,
        )
        exact_evaluation.verify_observation_support_exact_lift_v1(
            registered,
            bridge,
            audit,
            lift,
        )
        access_order = ExactAccessOrderAttestationV1(
            freeze.freeze_id,
            lift.evaluation_id,
            exact_evaluation.EVALUATION_ONLY,
        )
        direct_result = RouteResultV1(
            registered.context_id,
            CampaignRoute.DIRECT,
            RouteClosure.CONDITIONAL_PLAN_CANDIDATE,
            checkpoint,
            bridge,
            audit,
            freeze,
            access_order,
            lift,
            None,
        )
    else:
        last = executions[-1]
        assert last.direct_audit is not None
        freeze = OperationalRouteFreezeV1(
            registered.context_id,
            CampaignRoute.DIRECT,
            last.checkpoint,
            last.bridge.bridge_id,
            last.direct_audit.model_id,
            last.direct_audit.audit_id,
            last.direct_audit.threshold_profile_id,
            last.direct_audit.audit_id,
            _route_trace_prefix_id(
                executions,
                CampaignRoute.DIRECT,
            ),
            OperationalFreezeOutcome.ROBUST_NO_SOUND_COVER,
        )
        _ = freeze.freeze_id
        fallback = exact_evaluation.run_observation_support_exact_fallback_v1(
            registered,
            prerequisite_operational_freeze_id=freeze.freeze_id,
        )
        access_order = ExactAccessOrderAttestationV1(
            freeze.freeze_id,
            fallback.fallback_result_id,
            exact_evaluation.FALLBACK_EXACT,
        )
        direct_result = RouteResultV1(
            registered.context_id,
            CampaignRoute.DIRECT,
            (
                RouteClosure.EXACT_FEASIBLE_FALLBACK
                if fallback.feasible_plan_certified
                else RouteClosure.NONCERTIFICATE
            ),
            None,
            None,
            None,
            freeze,
            access_order,
            None,
            fallback,
        )

    if quotient_terminal is None:
        last = executions[-1]
        assert last.quotient_base_audit is not None
        freeze = OperationalRouteFreezeV1(
            registered.context_id,
            CampaignRoute.QUOTIENT,
            last.checkpoint,
            last.bridge.bridge_id,
            last.quotient_base_audit.model_id,
            last.quotient_base_audit.audit_id,
            last.quotient_base_audit.threshold_profile_id,
            (
                last.quotient_refinement.result_id
                if last.quotient_refinement is not None
                else last.quotient_base_audit.audit_id
            ),
            _route_trace_prefix_id(
                executions,
                CampaignRoute.QUOTIENT,
            ),
            OperationalFreezeOutcome.ROBUST_NO_SOUND_COVER,
        )
        _ = freeze.freeze_id
        fallback = exact_evaluation.run_observation_support_exact_fallback_v1(
            registered,
            prerequisite_operational_freeze_id=freeze.freeze_id,
        )
        access_order = ExactAccessOrderAttestationV1(
            freeze.freeze_id,
            fallback.fallback_result_id,
            exact_evaluation.FALLBACK_EXACT,
        )
        quotient_result = RouteResultV1(
            registered.context_id,
            CampaignRoute.QUOTIENT,
            (
                RouteClosure.EXACT_FEASIBLE_FALLBACK
                if fallback.feasible_plan_certified
                else RouteClosure.NONCERTIFICATE
            ),
            None,
            None,
            None,
            freeze,
            access_order,
            None,
            fallback,
        )
    else:
        checkpoint, bridge, audit = quotient_terminal
        selected_execution = next(
            item
            for item in executions
            if item.checkpoint == checkpoint
        )
        terminal_proof_id = (
            selected_execution.quotient_refinement.result_id
            if (
                selected_execution.quotient_refinement is not None
                and (
                    selected_execution.quotient_refinement
                    .selected_audit_id
                    == audit.audit_id
                )
            )
            else (
                selected_execution.promoted_consumer_result.consumer_id
                if (
                    selected_execution.promoted_consumer_result is not None
                    and (
                        selected_execution.promoted_consumer_result
                        .audit.audit_id
                        == audit.audit_id
                    )
                )
                else audit.audit_id
            )
        )
        freeze = OperationalRouteFreezeV1(
            registered.context_id,
            CampaignRoute.QUOTIENT,
            checkpoint,
            bridge.bridge_id,
            audit.model_id,
            audit.audit_id,
            audit.threshold_profile_id,
            terminal_proof_id,
            _route_trace_prefix_id(
                executions,
                CampaignRoute.QUOTIENT,
            ),
            OperationalFreezeOutcome.ROBUST_PLAN_CERTIFIED,
        )
        _ = freeze.freeze_id
        lift = exact_evaluation.evaluate_observation_support_exact_lift_v1(
            registered,
            bridge,
            audit,
            prerequisite_operational_freeze_id=freeze.freeze_id,
        )
        exact_evaluation.verify_observation_support_exact_lift_v1(
            registered,
            bridge,
            audit,
            lift,
        )
        access_order = ExactAccessOrderAttestationV1(
            freeze.freeze_id,
            lift.evaluation_id,
            exact_evaluation.EVALUATION_ONLY,
        )
        quotient_result = RouteResultV1(
            registered.context_id,
            CampaignRoute.QUOTIENT,
            RouteClosure.CONDITIONAL_PLAN_CANDIDATE,
            checkpoint,
            bridge,
            audit,
            freeze,
            access_order,
            lift,
            None,
        )

    physical_ids = direct_ids | quotient_ids
    accounting = RawPrefixAccountingV1(
        direct_rebuild,
        quotient_rebuild,
        len(direct_ids),
        len(quotient_ids),
        len(physical_ids),
        tuple(sorted(direct_ids)),
        tuple(sorted(quotient_ids)),
        tuple(sorted(physical_ids)),
        tuple(sorted(closure_ids)),
    )
    return ContextCampaignResultV1(
        registered,
        tuple(executions),
        executions[0].bridge.other_escape_handler,
        direct_result,
        quotient_result,
        accounting,
    )


def _context_operational_trace_id(
    context_result: ContextCampaignResultV1,
) -> str:
    return _content_id(
        "context_operational_trace",
        {
            "schema": "acfqp.observation_support_context_operational_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_result.context.context_id,
            "execution_ids": [
                item.execution_id for item in context_result.executions
            ],
            "direct_operational_freeze_id": (
                context_result.direct_result.operational_freeze.freeze_id
            ),
            "quotient_operational_freeze_id": (
                context_result.quotient_result.operational_freeze.freeze_id
            ),
            "accounting_id": context_result.accounting.accounting_id,
            "evaluation_or_fallback_artifact_ids_in_identity": [],
        },
    )


def _planning_trace_id(
    context_results: tuple[ContextCampaignResultV1, ...],
) -> str:
    return _content_id(
        "planning_trace",
        {
            "schema": "acfqp.observation_support_planning_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "context_operational_trace_ids": [
                _context_operational_trace_id(item)
                for item in context_results
            ],
            "registered_checkpoints": list(REGISTERED_CHECKPOINTS),
            "all_considered_rule": (
                "EVERY_ROW_EPOCH_USED_BY_EVERY_ACTIVE_ROUTE_IN_CHRONOLOGY"
            ),
        },
    )


def _manifest_and_evidence(
    context_results: tuple[ContextCampaignResultV1, ...],
) -> tuple[
    family_confidence.PlanningRowEpochManifestV1,
    tuple[family_confidence.PartialSupportRowEpochEvidenceV1, ...],
]:
    trace_id = _planning_trace_id(context_results)
    considerations: list[
        family_confidence.PlanningRowEpochConsiderationV1
    ] = []
    evidence_by_identity: dict[
        str,
        family_confidence.PartialSupportRowEpochEvidenceV1,
    ] = {}
    sequence = 0
    for context_result in context_results:
        for execution in context_result.executions:
            consumers: list[
                tuple[str, family_confidence.PlanningConsumerKindV1]
            ] = []
            if execution.direct_considered:
                consumers.append(
                    (
                        _content_id(
                            "logical_consumer",
                            {
                                "context_operational_trace_id": (
                                    _context_operational_trace_id(
                                        context_result
                                    )
                                ),
                                "checkpoint_execution_id": (
                                    execution.execution_id
                                ),
                                "route": CampaignRoute.DIRECT.value,
                                "stage": "DIRECT_AUDIT",
                            },
                        ),
                        family_confidence.PlanningConsumerKindV1.DIRECT,
                    )
                )
            if execution.quotient_considered:
                consumers.append(
                    (
                        _content_id(
                            "logical_consumer",
                            {
                                "context_operational_trace_id": (
                                    _context_operational_trace_id(
                                        context_result
                                    )
                                ),
                                "checkpoint_execution_id": (
                                    execution.execution_id
                                ),
                                "route": CampaignRoute.QUOTIENT.value,
                                "stage": "BASE_QUOTIENT_AUDIT",
                            },
                        ),
                        family_confidence.PlanningConsumerKindV1.QUOTIENT,
                    )
                )
                if execution.quotient_refinement is not None:
                    for candidate in (
                        execution.quotient_refinement.candidate_traces
                    ):
                        consumers.append(
                            (
                                _content_id(
                                    "logical_consumer",
                                    {
                                        "context_operational_trace_id": (
                                            _context_operational_trace_id(
                                                context_result
                                            )
                                        ),
                                        "checkpoint_execution_id": (
                                            execution.execution_id
                                        ),
                                        "route": (
                                            CampaignRoute.QUOTIENT.value
                                        ),
                                        "stage": (
                                            "TARGET_COORDINATE_CANDIDATE"
                                        ),
                                        "candidate_trace_id": (
                                            candidate.candidate_trace_id
                                        ),
                                    },
                                ),
                                (
                                    family_confidence
                                    .PlanningConsumerKindV1.PLANNER_AUDIT
                                ),
                            )
                        )
                if execution.support_expansion_authorization is not None:
                    for evidence in (
                        execution.support_expansion_authorization
                        .candidate_evidence
                    ):
                        consumers.append(
                            (
                                _content_id(
                                    "logical_consumer",
                                    {
                                        "context_operational_trace_id": (
                                            _context_operational_trace_id(
                                                context_result
                                            )
                                        ),
                                        "checkpoint_execution_id": (
                                            execution.execution_id
                                        ),
                                        "route": (
                                            CampaignRoute.QUOTIENT.value
                                        ),
                                        "stage": (
                                            "SUPPORT_EXPANSION_CAUSAL_"
                                            "COUNTERFACTUAL"
                                        ),
                                        "causal_evidence_id": (
                                            evidence.evidence_id
                                        ),
                                    },
                                ),
                                (
                                    family_confidence
                                    .PlanningConsumerKindV1.PLANNER_AUDIT
                                ),
                            )
                        )
            for consumer_id, kind in consumers:
                consumer_id = _content_id(
                    "manifest_consumer_binding",
                    {"logical_consumer_id": consumer_id},
                )
                for row in execution.closure.all_rows:
                    consideration = (
                        family_confidence
                        .bind_planning_row_epoch_consideration_v1(
                            planning_trace_id=trace_id,
                            sequence_index=sequence,
                            logical_consumer_id=consumer_id,
                            consumer_kind=kind,
                            row=row,
                        )
                    )
                    considerations.append(consideration)
                    sequence += 1
                    evidence = (
                        family_confidence
                        .bind_partial_support_row_epoch_evidence_v1(
                            row,
                            _row_replay_reference(row),
                        )
                    )
                    evidence_by_identity[
                        evidence.row_epoch_identity.identity_id
                    ] = evidence
            if execution.promoted_consumer_result is not None:
                promoted = execution.promoted_consumer_result
                consumer_id = _content_id(
                    "manifest_consumer_binding",
                    {
                        "logical_consumer_id": _content_id(
                            "logical_consumer",
                            {
                                "context_operational_trace_id": (
                                    _context_operational_trace_id(
                                        context_result
                                    )
                                ),
                                "checkpoint_execution_id": (
                                    execution.execution_id
                                ),
                                "stage": "PROMOTED_SUPPORT_REPLAN",
                                "promoted_consumer_id": (
                                    promoted.consumer_id
                                ),
                            },
                        )
                    },
                )
                for row in promoted.promoted_closure.all_rows:
                    consideration = (
                        family_confidence
                        .bind_planning_row_epoch_consideration_v1(
                            planning_trace_id=trace_id,
                            sequence_index=sequence,
                            logical_consumer_id=consumer_id,
                            consumer_kind=(
                                family_confidence
                                .PlanningConsumerKindV1.PLANNER_AUDIT
                            ),
                            row=row,
                        )
                    )
                    considerations.append(consideration)
                    sequence += 1
                    evidence = (
                        family_confidence
                        .bind_partial_support_row_epoch_evidence_v1(
                            row,
                            _row_replay_reference(row),
                        )
                    )
                    evidence_by_identity[
                        evidence.row_epoch_identity.identity_id
                    ] = evidence
    manifest = family_confidence.freeze_planning_row_epoch_manifest_v1(
        trace_id,
        tuple(considerations),
    )
    evidences = tuple(
        evidence_by_identity[item]
        for item in sorted(evidence_by_identity)
    )
    return manifest, evidences


def _terminal_class(result: RouteResultV1) -> str:
    if result.closure is RouteClosure.CONDITIONAL_PLAN_CANDIDATE:
        return "CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE"
    if result.closure is RouteClosure.EXACT_FEASIBLE_FALLBACK:
        return "EXACT_FEASIBLE_FALLBACK"
    return "NONCERTIFICATE"


def _campaign_counters(
    results: tuple[ContextCampaignResultV1, ...],
) -> CampaignCounterSummaryV1:
    longest_base_row: dict[
        tuple[str, str],
        acquisition.GraphPartialSupportRowV1,
    ] = {}
    support_epoch_ids: set[str] = set()
    base_model_builds = 0
    candidate_model_builds = 0
    expansion_candidate_models = 0
    promoted_model_builds = 0
    direct_audits = 0
    quotient_audits = 0
    candidate_audits = 0
    expansion_candidate_audits = 0
    promoted_audits = 0
    promotion_words = 0
    promotion_rejections = 0
    promotion_draws = 0
    promoted_epochs = 0
    promoted_outcomes = 0
    fallback_rows = 0
    standalone_rows = 0
    for result in results:
        for execution in result.executions:
            base_model_builds += 1
            direct_audits += int(execution.direct_audit is not None)
            quotient_audits += int(
                execution.quotient_base_audit is not None
            )
            if execution.quotient_refinement is not None:
                count = len(execution.quotient_refinement.candidate_traces)
                candidate_model_builds += count
                candidate_audits += count
            if execution.support_expansion_authorization is not None:
                count = len(
                    execution.support_expansion_authorization
                    .candidate_evidence
                )
                expansion_candidate_models += count
                expansion_candidate_audits += count
            for row in execution.closure.all_rows:
                key = (result.context.context_id, row.binding.row_id)
                previous = longest_base_row.get(key)
                if (
                    previous is None
                    or row.counters.total_observer_draws
                    > previous.counters.total_observer_draws
                ):
                    longest_base_row[key] = row
                support_epoch_ids.add(row.support_epoch.support_epoch_id)
            if execution.promoted_consumer_result is not None:
                promoted = execution.promoted_consumer_result
                promoted_model_builds += 1
                promoted_audits += 1
                promoted_epochs += 1
                promoted_outcomes += len(
                    promoted.promoted_closure.replacement.authorization
                    .selected_novel_outcome_ids
                )
                promotion_draws += (
                    promoted.counters.incremental_observer_draws
                )
                promotion_words += (
                    promoted.counters.incremental_random_word_calls
                )
                promotion_rejections += (
                    promoted.counters.incremental_rejections
                )
                support_epoch_ids.update(
                    row.support_epoch.support_epoch_id
                    for row in promoted.promoted_closure.all_rows
                )
        for route in (result.direct_result, result.quotient_result):
            if route.exact_fallback is not None:
                fallback_rows += (
                    route.exact_fallback.counters.exact_state_action_rows
                )
            if route.exact_lift is not None:
                standalone_rows += (
                    route.exact_lift.counters.total_evaluation_exact_row_calls
                )
    rows = tuple(longest_base_row.values())
    unique_draws = sum(
        item.counters.total_observer_draws for item in rows
    ) + promotion_draws
    unique_words = sum(
        item.counters.total_random_word_calls for item in rows
    ) + promotion_words
    unique_rejections = sum(
        item.counters.total_rejections for item in rows
    ) + promotion_rejections
    physical_ids = {
        item
        for result in results
        for item in result.accounting.physical_unique_observation_ids
    }
    if unique_draws != len(physical_ids):
        raise ObservationSupportCampaignInvariantViolation(
            "physical random-work suffix accounting differs from raw-ID union"
        )
    return CampaignCounterSummaryV1(
        unique_draws,
        unique_words,
        unique_rejections,
        sum(
            item.accounting.direct_rebuild_observer_draws
            for item in results
        ),
        sum(
            item.accounting.quotient_rebuild_observer_draws
            for item in results
        ),
        len(support_epoch_ids),
        promoted_epochs,
        promoted_outcomes,
        base_model_builds,
        candidate_model_builds,
        expansion_candidate_models,
        promoted_model_builds,
        direct_audits,
        quotient_audits,
        candidate_audits,
        expansion_candidate_audits,
        promoted_audits,
        fallback_rows,
        standalone_rows,
    )


def run_observation_support_campaign_v1(
    *,
    max_workers: int = 1,
) -> (
    ObservationSupportCampaignV1
    | ObservationSupportCampaignFamilyCapExhaustedV1
):
    """Run the complete preregistered V0-068 campaign."""

    contexts = {
        item.context_key: item
        for item in observer.registered_public_graph_contexts_v1()
    }
    if type(max_workers) is not int or isinstance(max_workers, bool):
        raise ObservationSupportCampaignInvariantViolation(
            "campaign worker budget must be an integer"
        )
    if max_workers < 1 or max_workers > h2_closure.MAX_PROCESS_WORKERS:
        raise ObservationSupportCampaignInvariantViolation(
            "campaign worker budget is outside the registered cap"
        )
    # Contexts are independent.  A bounded outer thread layer coordinates
    # their process pools while the exact total process budget remains at or
    # below max_workers.  Execution width is intentionally absent from every
    # content identity.
    context_width = (
        1
        if max_workers < len(REGISTERED_CONTEXT_ORDER)
        else len(REGISTERED_CONTEXT_ORDER)
    )
    if context_width == 1:
        results = tuple(
            run_observation_support_context_v1(
                contexts[key],
                max_workers=max_workers,
            )
            for key in REGISTERED_CONTEXT_ORDER
        )
    else:
        w5_workers = max(1, max_workers // 8)
        remaining_workers = max_workers - w5_workers
        k6_workers = max(1, remaining_workers // 2)
        no_cover_workers = remaining_workers - k6_workers
        worker_budget_by_key = {
            "opaque_graph_w5_v0": w5_workers,
            "opaque_graph_k6_v0": k6_workers,
            "opaque_graph_k6_minus_edge_v0": no_cover_workers,
        }
        if sum(worker_budget_by_key.values()) != max_workers:
            raise ObservationSupportCampaignInvariantViolation(
                "context worker allocation does not reconcile"
            )
        with ThreadPoolExecutor(max_workers=context_width) as executor:
            futures = {
                key: executor.submit(
                    run_observation_support_context_v1,
                    contexts[key],
                    max_workers=worker_budget_by_key[key],
                )
                for key in REGISTERED_CONTEXT_ORDER
            }
            by_key = {
                key: futures[key].result()
                for key in REGISTERED_CONTEXT_ORDER
            }
        results = tuple(by_key[key] for key in REGISTERED_CONTEXT_ORDER)
    manifest, evidences = _manifest_and_evidence(results)
    family = family_confidence.build_partial_support_family_confidence_v1(
        manifest,
        evidences,
    )
    if type(family) is family_confidence.PartialSupportFamilyCapExhaustedV1:
        return ObservationSupportCampaignFamilyCapExhaustedV1(
            results,
            manifest,
            family,
        )
    if (
        type(family)
        is not family_confidence.PartialSupportFamilyConfidenceAuthorityV1
    ):
        raise ObservationSupportCampaignInvariantViolation(
            "family builder returned an unknown closure type"
        )
    family_confidence.verify_partial_support_family_confidence_v1(
        family,
        manifest,
        evidences,
    )
    envelopes = tuple(
        ConditionalTerminalEnvelopeV1(
            context_result.context_result_id,
            route_result.route_result_id,
            family.authority_id,
            route_result.route,
            _terminal_class(route_result),
        )
        for context_result in results
        for route_result in (
            context_result.direct_result,
            context_result.quotient_result,
        )
    )
    direct = sum(
        item.accounting.direct_unique_observer_draws for item in results
    )
    quotient = sum(
        item.accounting.quotient_unique_observer_draws for item in results
    )
    physical = len(
        {
            observation_id
            for item in results
            for observation_id in (
                item.accounting.physical_unique_observation_ids
            )
        }
    )
    positives = tuple(
        item
        for item in results
        if item.context.context_key in POSITIVE_CONTEXT_KEYS
    )
    negative = next(
        item
        for item in results
        if item.context.context_key == NO_COVER_CONTEXT_KEY
    )
    construction = (
        all(
            item.direct_result.closure
            is RouteClosure.CONDITIONAL_PLAN_CANDIDATE
            and item.quotient_result.closure
            is RouteClosure.CONDITIONAL_PLAN_CANDIDATE
            for item in positives
        )
        and negative.quotient_result.closure
        is RouteClosure.EXACT_FEASIBLE_FALLBACK
        and negative.direct_result.closure
        is RouteClosure.EXACT_FEASIBLE_FALLBACK
    )
    advantage = (
        construction
        and quotient < direct
        and all(
            item.accounting.quotient_unique_observer_draws
            <= item.accounting.direct_unique_observer_draws
            for item in positives
        )
    )
    return ObservationSupportCampaignV1(
        results,
        manifest,
        family,
        envelopes,
        _campaign_counters(results),
        construction,
        advantage,
        direct,
        quotient,
        physical,
    )


@dataclass(frozen=True, slots=True)
class ObservationSupportCampaignVerificationV1:
    campaign_id: str
    replayed_campaign_id: str
    replayed_row_ids: tuple[str, ...]
    replayed_row_verification_ids: tuple[str, ...]
    family_verification_id: str
    role_manifest: DurableVerifiedRoleManifestV1
    same_implementation_full_replay: bool = True
    independent_implementation_claimed: bool = False
    exact_iid_implementation_claimed: bool = False
    formal_exact_iid_plan_certificate: bool = False
    valid: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.campaign_id, "verified campaign"),
            (self.replayed_campaign_id, "replayed campaign"),
            (self.family_verification_id, "family verification"),
        ):
            _cid(value, field)
        if (
            self.campaign_id != self.replayed_campaign_id
            or type(self.replayed_row_ids) is not tuple
            or type(self.replayed_row_verification_ids) is not tuple
            or len(self.replayed_row_ids)
            != len(self.replayed_row_verification_ids)
            or self.replayed_row_ids
            != tuple(sorted(set(self.replayed_row_ids)))
            or any(
                _cid(item, "row replay verification") != item
                for item in self.replayed_row_verification_ids
            )
            or type(self.role_manifest)
            is not DurableVerifiedRoleManifestV1
            or self.role_manifest.campaign_id != self.campaign_id
            or {
                item.artifact_id
                for item in self.role_manifest.bindings
                if item.artifact_role
                == "RAW_PARTIAL_SUPPORT_ROW_REPLAY"
            }
            != set(self.replayed_row_ids)
            or self.same_implementation_full_replay is not True
            or self.independent_implementation_claimed is not False
            or self.exact_iid_implementation_claimed is not False
            or self.formal_exact_iid_plan_certificate is not False
            or self.valid is not True
        ):
            raise ObservationSupportCampaignInvariantViolation(
                "campaign verification is incomplete or overstated"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_campaign_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "replayed_campaign_id": self.replayed_campaign_id,
            "replayed_row_ids": list(self.replayed_row_ids),
            "replayed_row_verification_ids": list(
                self.replayed_row_verification_ids
            ),
            "family_verification_id": self.family_verification_id,
            "role_manifest_id": self.role_manifest.manifest_id,
            "same_implementation_full_replay": True,
            "independent_implementation_claimed": False,
            "exact_iid_implementation_claimed": False,
            "formal_exact_iid_plan_certificate": False,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("campaign_verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "role_manifest": self.role_manifest.to_document(),
            "verification_id": self.verification_id,
        }


def _row_catalogue(
    closure: Any,
    row: acquisition.GraphPartialSupportRowV1,
) -> observer.LegalActionCatalogueV1:
    by_id = {item.catalogue_id: item for item in _catalogues(closure)}
    catalogue = by_id.get(row.binding.catalogue_id)
    if catalogue is None:
        raise ObservationSupportCampaignInvariantViolation(
            "row replay lacks its public legal-action catalogue"
        )
    return catalogue


def verify_observation_support_campaign_v1(
    claimed: ObservationSupportCampaignV1,
    *,
    max_workers: int = 1,
) -> ObservationSupportCampaignVerificationV1:
    """Full same-implementation replay, including every physical row.

    The verifier does not trust the claimed all-considered manifest.  It
    mechanically reconstructs chronology from checkpoint executions, invokes
    the raw row semantic replay for every unique row artifact, rebuilds the
    family authority, and finally reruns the complete campaign.
    """

    if type(claimed) is not ObservationSupportCampaignV1:
        raise ObservationSupportCampaignInvariantViolation(
            "campaign verifier requires the concrete campaign artifact"
        )
    reconstructed_manifest, reconstructed_evidences = (
        _manifest_and_evidence(claimed.context_results)
    )
    if (
        reconstructed_manifest.manifest_id
        != claimed.family_manifest.manifest_id
        or reconstructed_manifest.to_document()
        != claimed.family_manifest.to_document()
    ):
        raise ObservationSupportCampaignInvariantViolation(
            "claimed family manifest omits or reorders considered row epochs"
        )
    row_verification_by_id: dict[str, str] = {}
    role_by_key: dict[
        tuple[str, str],
        VerifiedArtifactRoleBindingV1,
    ] = {}

    def bind(role: str, artifact_id: str, verification_id: str) -> None:
        binding = VerifiedArtifactRoleBindingV1(
            role,
            artifact_id,
            verification_id,
        )
        role_by_key.setdefault((role, artifact_id), binding)

    closure_by_id: dict[
        str,
        tuple[
            observer.PublicGraphContextV1,
            h2_closure.ObservationSupportH2ClosureV1,
        ],
    ] = {}
    promoted_row_by_id: dict[
        str,
        grouped_replay.GroupedRowReplayRequestV1,
    ] = {}
    for context_result in claimed.context_results:
        handler_verification_id = _content_id(
            "other_escape_handler_verification",
            {
                "handler_id": (
                    context_result.other_escape_handler.handler_id
                ),
                "context_id": context_result.context.context_id,
                "other_destination_id": (
                    context_result.other_escape_handler
                    .other_destination_id
                ),
                "event_key": context_result.other_escape_handler.event_key,
                "behavior": context_result.other_escape_handler.behavior,
                "failure_value": _fdoc(Fraction(1)),
                "continuation_reward_lower": _fdoc(Fraction(0)),
                "requires_ground_action": False,
                "valid": True,
            },
        )
        bind(
            "REGISTERED_OTHER_ABSORBING_ABORT_HANDLER",
            context_result.other_escape_handler.handler_id,
            handler_verification_id,
        )
        for execution in context_result.executions:
            closure_by_id.setdefault(
                execution.closure.closure_id,
                (context_result.context, execution.closure),
            )
            bridge_verification = (
                graph_model.verify_observation_support_graph_models_v1(
                    context=context_result.context,
                    root_catalogue=execution.closure.root_catalogue,
                    catalogues=_catalogues(execution.closure),
                    partial_rows=execution.closure.all_rows,
                    bridge=execution.bridge,
                )
            )
            bind(
                "AUTHORITY_BOUND_BASE_MODEL_BRIDGE",
                execution.bridge.bridge_id,
                bridge_verification.verification_id,
            )
            if execution.direct_audit is not None:
                verification = robust.verify_robust_plan_audit_v1(
                    execution.bridge.direct_model,
                    execution.threshold,
                    execution.direct_audit,
                )
                bind(
                    "DIRECT_ROBUST_AUDIT",
                    execution.direct_audit.audit_id,
                    verification.verification_id,
                )
            if execution.quotient_base_audit is not None:
                verification = robust.verify_robust_plan_audit_v1(
                    execution.bridge.quotient_model,
                    execution.threshold,
                    execution.quotient_base_audit,
                )
                bind(
                    "BASE_QUOTIENT_ROBUST_AUDIT",
                    execution.quotient_base_audit.audit_id,
                    verification.verification_id,
                )
            if execution.quotient_refinement is not None:
                verification = (
                    refinement
                    .verify_observation_support_coordinate_refinement_v1(
                        context=context_result.context,
                        closure=execution.closure,
                        base_bridge=execution.bridge,
                        failed_audit=execution.quotient_base_audit,
                        claimed=execution.quotient_refinement,
                    )
                )
                bind(
                    "TARGET_OBSERVATION_ONLY_COORDINATE_REFINEMENT",
                    execution.quotient_refinement.result_id,
                    verification.verification_id,
                )
            if execution.promoted_consumer_result is not None:
                verification = (
                    promoted_consumer
                    .verify_partial_support_promoted_h2_consumer_v1(
                        context=context_result.context,
                        parent_closure=execution.closure,
                        parent_bridge=execution.bridge,
                        parent_audit=execution.quotient_base_audit,
                        threshold=execution.threshold,
                        replacement=execution.promoted_replacement,
                        claimed=execution.promoted_consumer_result,
                        max_workers=max_workers,
                    )
                )
                bind(
                    "CAUSAL_SUPPORT_EXPANSION_AUTHORIZATION",
                    (
                        execution.support_expansion_authorization
                        .authorization_id
                    ),
                    verification.verification_id,
                )
                bind(
                    "FRESH_PROMOTED_ROW_REPLACEMENT",
                    execution.promoted_replacement.replacement_id,
                    verification.verification_id,
                )
                bind(
                    "PROMOTED_MIXED_EPOCH_CLOSURE_REPLAN",
                    execution.promoted_consumer_result.consumer_id,
                    verification.verification_id,
                )
                bind(
                    "FAILED_PROMOTED_ROBUST_AUDIT",
                    execution.promoted_consumer_result.audit.audit_id,
                    execution.promoted_consumer_result.audit_replay.verification_id,
                )
                promoted_closure = (
                    execution.promoted_consumer_result.promoted_closure
                )
                for row in promoted_closure.all_rows:
                    request = grouped_replay.GroupedRowReplayRequestV1(
                        context_result.context,
                        _row_catalogue(promoted_closure, row),
                        row,
                    )
                    previous_request = promoted_row_by_id.setdefault(
                        row.partial_row_id,
                        request,
                    )
                    if previous_request != request:
                        raise ObservationSupportCampaignInvariantViolation(
                            "one promoted row ID has two replay requests"
                        )
    closure_items = tuple(
        closure_by_id[item] for item in sorted(closure_by_id)
    )
    request_by_row_id: dict[
        str,
        grouped_replay.GroupedRowReplayRequestV1,
    ] = {}

    def register_grouped_request(
        request: grouped_replay.GroupedRowReplayRequestV1,
    ) -> None:
        previous = request_by_row_id.setdefault(
            request.partial_row_id,
            request,
        )
        if previous != request:
            raise ObservationSupportCampaignInvariantViolation(
                "one partial row ID is bound to two grouped replay requests"
            )

    for context, closure in closure_items:
        for row in closure.all_rows:
            register_grouped_request(
                grouped_replay.GroupedRowReplayRequestV1(
                    context,
                    _row_catalogue(closure, row),
                    row,
                )
            )
    for request in promoted_row_by_id.values():
        register_grouped_request(request)
    grouped_result = (
        grouped_replay.grouped_verify_graph_partial_support_rows_v1(
            request_by_row_id.values(),
            max_workers=max_workers,
        )
    )
    grouped_verification_by_id = (
        grouped_result.verification_by_partial_row_id
    )
    closure_verifications = tuple(
        grouped_replay
        .verify_observation_support_h2_closure_from_grouped_rows_v1(
            context,
            closure,
            grouped_verification_by_id,
        )
        for context, closure in closure_items
    )
    for (_, closure), closure_verification in zip(
        closure_items,
        closure_verifications,
    ):
        bind(
            "OBSERVATION_ONLY_H2_CLOSURE",
            closure.closure_id,
            closure_verification.verification_id,
        )
        for partial_row_id, verification_id in (
            closure_verification.row_replay_bindings
        ):
            previous = row_verification_by_id.setdefault(
                partial_row_id,
                verification_id,
            )
            if previous != verification_id:
                raise ObservationSupportCampaignInvariantViolation(
                    "one partial row replayed to two semantic identities"
                )
    for partial_row_id, verification in sorted(
        grouped_verification_by_id.items()
    ):
        previous = row_verification_by_id.setdefault(
            partial_row_id,
            verification.verification_id,
        )
        if previous != verification.verification_id:
            raise ObservationSupportCampaignInvariantViolation(
                "retained promoted row replay differs from base replay"
            )
    family_verification = (
        family_confidence.verify_partial_support_family_confidence_v1(
            claimed.family_authority,
            reconstructed_manifest,
            reconstructed_evidences,
        )
    )
    family_row_ids = {
        item.row.partial_row_id for item in reconstructed_evidences
    }
    if set(row_verification_by_id) != family_row_ids:
        raise ObservationSupportCampaignInvariantViolation(
            "raw replay list differs from all family-evidence rows"
        )
    for partial_row_id, verification_id in sorted(
        row_verification_by_id.items()
    ):
        bind(
            "RAW_PARTIAL_SUPPORT_ROW_REPLAY",
            partial_row_id,
            verification_id,
        )
    bind(
        "CLOSED_ALL_CONSIDERED_FAMILY_CONFIDENCE",
        claimed.family_authority.authority_id,
        family_verification.verification_id,
    )
    for context_result in claimed.context_results:
        for route_result in (
            context_result.direct_result,
            context_result.quotient_result,
        ):
            if route_result.operational_freeze is not None:
                freeze_verification_id = _content_id(
                    "operational_freeze_verification",
                    {
                        "freeze_id": route_result.operational_freeze.freeze_id,
                        "bridge_id": (
                            route_result.operational_freeze.bridge_id
                        ),
                        "audit_id": (
                            route_result.operational_freeze.audit_id
                        ),
                        "terminal_route_proof_id": (
                            route_result.operational_freeze
                            .terminal_route_proof_id
                        ),
                        "planning_trace_prefix_id": (
                            route_result.operational_freeze
                            .planning_trace_prefix_id
                        ),
                        "valid": True,
                        "exact_queries_before_freeze": 0,
                    },
                )
                bind(
                    "PRE_EXACT_OPERATIONAL_ROUTE_FREEZE",
                    route_result.operational_freeze.freeze_id,
                    freeze_verification_id,
                )
                access_verification_id = _content_id(
                    "exact_access_order_verification",
                    {
                        "attestation_id": (
                            route_result.exact_access_order.attestation_id
                        ),
                        "operational_freeze_id": (
                            route_result.operational_freeze.freeze_id
                        ),
                        "sequence": [
                            "OPERATIONAL_ROUTE_FREEZE",
                            "EXACT_AUTHORITY_ACCESS",
                        ],
                        "valid": True,
                    },
                )
                bind(
                    "EXACT_ACCESS_ORDER_ATTESTATION",
                    route_result.exact_access_order.attestation_id,
                    access_verification_id,
                )
            if route_result.exact_lift is not None:
                verification = (
                    exact_evaluation
                    .verify_observation_support_exact_lift_v1(
                        context_result.context,
                        route_result.bridge,
                        route_result.audit,
                        route_result.exact_lift,
                    )
                )
                bind(
                    "STANDALONE_EXACT_LIFT_EVALUATION",
                    route_result.exact_lift.evaluation_id,
                    verification.verification_id,
                )
            if route_result.exact_fallback is not None:
                replayed_fallback = (
                    exact_evaluation
                    .run_observation_support_exact_fallback_v1(
                        context_result.context,
                        max_exact_state_action_rows=(
                            route_result.exact_fallback.cap
                            .max_exact_state_action_rows
                        ),
                        prerequisite_operational_freeze_id=(
                            route_result.operational_freeze.freeze_id
                        ),
                    )
                )
                if replayed_fallback != route_result.exact_fallback:
                    raise ObservationSupportCampaignInvariantViolation(
                        "exact fallback differs from complete-search replay"
                    )
                fallback_verification_id = _content_id(
                    "exact_fallback_verification",
                    {
                        "fallback_result_id": (
                            replayed_fallback.fallback_result_id
                        ),
                        "search_id": replayed_fallback.search.search_id,
                        "cap_semantics": FALLBACK_CAP_SEMANTICS,
                        "valid": True,
                    },
                )
                bind(
                    "COMPLETE_SEARCH_POSTHOC_CAP_EXACT_FALLBACK",
                    replayed_fallback.fallback_result_id,
                    fallback_verification_id,
                )
    replayed = run_observation_support_campaign_v1(
        max_workers=max_workers,
    )
    if (
        replayed != claimed
        or replayed.campaign_id != claimed.campaign_id
        or canonical_json_bytes(replayed.to_document())
        != canonical_json_bytes(claimed.to_document())
    ):
        raise ObservationSupportCampaignInvariantViolation(
            "campaign differs from complete same-implementation replay"
        )
    bind(
        "COMPLETE_CAMPAIGN_SAME_IMPLEMENTATION_REPLAY",
        claimed.campaign_id,
        replayed.campaign_id,
    )
    role_manifest = DurableVerifiedRoleManifestV1(
        claimed.campaign_id,
        tuple(
            sorted(
                role_by_key.values(),
                key=lambda item: item.binding_id,
            )
        ),
    )
    return ObservationSupportCampaignVerificationV1(
        claimed.campaign_id,
        replayed.campaign_id,
        tuple(sorted(row_verification_by_id)),
        tuple(
            row_verification_by_id[item]
            for item in sorted(row_verification_by_id)
        ),
        family_verification.verification_id,
        role_manifest,
    )


__all__ = [
    "CONDITIONAL_SCOPE",
    "CONTRACT_VERSION",
    "CampaignRoute",
    "CampaignCounterSummaryV1",
    "CheckpointExecutionV1",
    "ConditionalTerminalEnvelopeV1",
    "ContextCampaignResultV1",
    "DurableVerifiedRoleManifestV1",
    "ExactAccessOrderAttestationV1",
    "FALLBACK_CAP_SEMANTICS",
    "NO_COVER_CONTEXT_KEY",
    "OTHER_SEMANTICS",
    "ObservationSupportCampaignInvariantViolation",
    "ObservationSupportCampaignV1",
    "ObservationSupportCampaignFamilyCapExhaustedV1",
    "ObservationSupportCampaignVerificationV1",
    "OperationalFreezeOutcome",
    "OperationalRouteFreezeV1",
    "POSITIVE_CONTEXT_KEYS",
    "PROFILE_KEY",
    "RANDOMNESS_IMPLEMENTATION",
    "REGISTERED_CHECKPOINTS",
    "REGISTERED_CONTEXT_ORDER",
    "RawPrefixAccountingV1",
    "RouteClosure",
    "RouteResultV1",
    "SCHEMA_VERSION",
    "VerifiedArtifactRoleBindingV1",
    "run_observation_support_campaign_v1",
    "run_observation_support_context_v1",
    "verify_observation_support_campaign_v1",
]
