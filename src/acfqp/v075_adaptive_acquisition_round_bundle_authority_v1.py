"""Pretarget round-bundle authority for V0-075 partial support recovery.

This component extends the proposal-only feature authority with the actual
two-round acquisition state machine.  It distinguishes:

* cold root discovery/validation work, which is never charged to the
  incremental cap;
* first materialization of a missing child action row
  (64 discovery + 8,192 validation draws);
* a 2,048-draw append to an already materialized selected validation prefix.

When a selected root row has an observed active successor whose child state
is absent from the partial learned graph, one candidate represents the
*complete* public legal-action catalogue of that child.  Its authorization
freezes every child discovery row, every dependent validation row, and, when
the selected root stream has room, one root-prefix promotion in the same
bundle.  If no child state is missing, ordinary selected-row promotions are
ranked instead.

All feature/midrank logic is delegated to the exact source-schema replay in
``v075_adaptive_acquisition_proposal_authority_v1``.  The prior changes only
the ordering score.  This module does not call an observer, kernel, private
law, reveal, salt, signer, random tape, or exact lift.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_adaptive_acquisition_proposal_authority_v1 as proposal
from acfqp import v075_batch_native_statistical_backend_v1 as batch_native
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as public_graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as backend


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_pretarget_adaptive_round_bundle_v1"
PRODUCTION_INTEGRATION_READY = False

MAX_ROUNDS = 2
CHILD_DISCOVERY_DRAWS = 64
CHILD_VALIDATION_DRAWS = 8_192
PROMOTION_DRAWS = 2_048
CHILD_ROW_INITIAL_DRAWS = CHILD_DISCOVERY_DRAWS + CHILD_VALIDATION_DRAWS
CHILD_VALIDATION_ACCEPTED_DRAW_CAP = (
    CHILD_VALIDATION_DRAWS + MAX_ROUNDS * PROMOTION_DRAWS
)
_ISSUER = object()

DOMAIN_TAGS = {
    "accounting": "acfqp:v075-adaptive-incremental-accounting:v1",
    "candidate": "acfqp:v075-adaptive-round-bundle-candidate:v1",
    "frontier": "acfqp:v075-adaptive-round-bundle-frontier:v1",
    "intent": "acfqp:v075-adaptive-round-bundle-row-intent:v1",
    "authorization": "acfqp:v075-adaptive-round-bundle-authorization:v1",
    "execution": "acfqp:v075-adaptive-round-bundle-execution:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 round-bundle content domains must be unique")


class V075AdaptiveRoundBundleInvariantViolation(ValueError):
    """A partial frontier, cost, cap, intent, or append invariant failed."""


class V075BundleCandidateKindV1(str, Enum):
    MISSING_CHILD_COMPLETE_CATALOGUE = (
        "MISSING_CHILD_COMPLETE_CATALOGUE"
    )
    SELECTED_ROW_VALIDATION_PROMOTION = (
        "SELECTED_ROW_VALIDATION_PROMOTION"
    )


class V075BundleIntentKindV1(str, Enum):
    EXISTING_VALIDATION_PREFIX_EXTENSION = (
        "EXISTING_VALIDATION_PREFIX_EXTENSION"
    )
    NEW_CHILD_ROW_DISCOVERY = "NEW_CHILD_ROW_DISCOVERY"
    NEW_CHILD_ROW_VALIDATION = "NEW_CHILD_ROW_VALIDATION"


class V075BundleAuthorizationStatusV1(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    NO_UNCERTAIN_PROOF_FRONTIER = "NO_UNCERTAIN_PROOF_FRONTIER"
    INCREMENTAL_CAP_EXHAUSTED = "INCREMENTAL_CAP_EXHAUSTED"


def _fail(message: str) -> None:
    raise V075AdaptiveRoundBundleInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075AdaptiveRoundBundleInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075AdaptiveRoundBundleInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("round-bundle arithmetic must use exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _registered_context(
    context_id: str,
) -> public_authority.V075PublicReplicateContextV1:
    _cid(context_id, "round-bundle context")
    values = tuple(
        item
        for item in (
            public_authority.freeze_v075_public_family_generation_v1()
            .replicate_contexts
        )
        if item.context_id == context_id
    )
    if len(values) != 1:
        _fail("round-bundle context is not preregistered")
    return values[0]


def _batch_groups(
    result: batch_native.V075BatchNativeBackendResultV1,
) -> dict[
    tuple[str, public_graph.V075ObservationLaneV1],
    tuple[Any, ...],
]:
    groups: dict[
        tuple[str, public_graph.V075ObservationLaneV1],
        list[Any],
    ] = {}
    for item in result.request.batches:
        stream = item.request.stream_identity
        groups.setdefault(
            (stream.row_binding_id, stream.lane),
            [],
        ).append(item)
    return {
        key: tuple(
            sorted(
                values,
                key=lambda item: (
                    item.request.stream_identity.observer_epoch_index,
                    item.request.stream_identity.stream_id,
                    item.request.accepted_draw_start,
                ),
            )
        )
        for key, values in groups.items()
    }


def _lane_draw_count(values: tuple[Any, ...]) -> int:
    return sum(item.request.accepted_draw_count for item in values)


@dataclass(frozen=True, slots=True)
class V075AdaptiveIncrementalAccountingV1:
    batch_result_id: str
    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    cold_root_draws: int
    new_child_action_row_ids: tuple[str, ...]
    new_child_materialization_draws: int
    validation_promotion_draws: int
    incremental_draws_used: int
    maximum_new_child_action_rows: int
    maximum_incremental_draws: int
    cap_profile_id: str

    def __post_init__(self) -> None:
        for value, name in (
            (self.batch_result_id, "accounting batch result"),
            (self.occurrence_id, "accounting occurrence"),
            (self.context_id, "accounting context"),
            (self.cap_profile_id, "accounting cap profile"),
        ):
            _cid(value, name)
        caps = worker.V075WorkerCapProfileV1()
        if (
            self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.new_child_action_row_ids
            != tuple(sorted(set(self.new_child_action_row_ids)))
            or self.cold_root_draws < 0
            or self.new_child_materialization_draws
            != len(self.new_child_action_row_ids) * CHILD_ROW_INITIAL_DRAWS
            or self.validation_promotion_draws < 0
            or self.validation_promotion_draws % PROMOTION_DRAWS
            or self.incremental_draws_used
            != self.new_child_materialization_draws
            + self.validation_promotion_draws
            or self.maximum_new_child_action_rows
            != caps.maximum_new_child_action_rows
            or self.maximum_incremental_draws
            != caps.maximum_incremental_draws_per_adaptive_arm
            or len(self.new_child_action_row_ids)
            > self.maximum_new_child_action_rows
            or self.incremental_draws_used > self.maximum_incremental_draws
            or self.cap_profile_id != caps.cap_profile_id
        ):
            _fail("incremental accounting is inconsistent or over cap")
        for item in self.new_child_action_row_ids:
            _cid(item, "accounted child row")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_incremental_accounting.v1",
            "schema_version": SCHEMA_VERSION,
            "batch_result_id": self.batch_result_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "cold_root_draws": self.cold_root_draws,
            "cold_root_draws_charged_to_incremental_cap": False,
            "new_child_action_row_ids": list(
                self.new_child_action_row_ids
            ),
            "new_child_materialization_draws": (
                self.new_child_materialization_draws
            ),
            "validation_promotion_draws": (
                self.validation_promotion_draws
            ),
            "incremental_draws_used": self.incremental_draws_used,
            "maximum_new_child_action_rows": (
                self.maximum_new_child_action_rows
            ),
            "maximum_incremental_draws": self.maximum_incremental_draws,
            "cap_profile_id": self.cap_profile_id,
            "exact_native_batch_replay": True,
        }

    @property
    def accounting_id(self) -> str:
        return _hash("accounting", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "accounting_id": self.accounting_id}


def replay_v075_incremental_accounting_v1(
    result: batch_native.V075BatchNativeBackendResultV1,
) -> V075AdaptiveIncrementalAccountingV1:
    """Classify every public batch draw as cold, child-base, or promotion."""

    if type(result) is not batch_native.V075BatchNativeBackendResultV1:
        _fail("incremental accounting requires one exact batch-native result")
    if result.request.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND:
        _fail("matched direct work does not use the adaptive incremental cap")
    context = result.request.context
    root = public_graph.root_catalogue_v1(context)
    root_rows = {
        public_graph.observation_row_binding_v1(
            context,
            root,
            action,
        ).row_binding_id
        for action in root.actions
    }
    groups = _batch_groups(result)
    all_row_ids = {row_id for row_id, _lane in groups}
    row_bindings: dict[str, public_graph.V075ObservationRowBindingV1] = {}
    for item in result.request.batches:
        binding = item.request.stream_identity.row_binding
        prior = row_bindings.setdefault(binding.row_binding_id, binding)
        if prior != binding:
            _fail("one row identity resolves to multiple typed row bindings")
    if not root_rows <= all_row_ids:
        _fail("adaptive batch history omits a cold root catalogue row")
    if any(
        (
            binding.remaining_horizon == 2
            and row_id not in root_rows
        )
        or (
            row_id not in root_rows
            and binding.remaining_horizon != 1
        )
        for row_id, binding in row_bindings.items()
    ):
        _fail("incremental accounting found a nonroot H=2 or non-H=1 row")
    child_rows = tuple(sorted(all_row_ids - root_rows))
    caps = worker.V075WorkerCapProfileV1()
    root_validation_cap = (
        caps.initial_validation_draws_per_row
        + caps.maximum_adaptive_rounds
        * caps.promotion_validation_draws_per_round
    )
    child_validation_cap = (
        caps.new_child_validation_draws_per_row
        + caps.maximum_adaptive_rounds
        * caps.promotion_validation_draws_per_round
    )
    cold = 0
    promotions = 0
    for row_id in sorted(all_row_ids):
        discovery = groups.get(
            (row_id, public_graph.V075ObservationLaneV1.DISCOVERY),
            (),
        )
        validation = groups.get(
            (row_id, public_graph.V075ObservationLaneV1.VALIDATION),
            (),
        )
        discovery_draws = _lane_draw_count(discovery)
        validation_draws = _lane_draw_count(validation)
        if (
            len(
                {
                    item.request.stream_identity.stream_id
                    for item in discovery
                }
            )
            != 1
            or len(
                {
                    item.request.stream_identity.stream_id
                    for item in validation
                }
            )
            != 1
            or {
                item.request.accepted_draw_cap for item in discovery
            }
            != {CHILD_DISCOVERY_DRAWS}
        ):
            _fail("row history changed its discovery/validation stream")
        if row_id in root_rows:
            if (
                discovery_draws
                != caps.initial_discovery_draws_per_row
                or validation_draws
                < caps.initial_validation_draws_per_row
                or (
                    validation_draws
                    - caps.initial_validation_draws_per_row
                )
                % PROMOTION_DRAWS
                or {
                    item.request.accepted_draw_cap for item in validation
                }
                != {root_validation_cap}
            ):
                _fail("root batch history is not cold-prefix plus promotions")
            cold += (
                caps.initial_discovery_draws_per_row
                + caps.initial_validation_draws_per_row
            )
            promotions += (
                validation_draws
                - caps.initial_validation_draws_per_row
            )
        else:
            if (
                discovery_draws != CHILD_DISCOVERY_DRAWS
                or validation_draws < CHILD_VALIDATION_DRAWS
                or (validation_draws - CHILD_VALIDATION_DRAWS)
                % PROMOTION_DRAWS
                or {
                    item.request.accepted_draw_cap for item in validation
                }
                != {child_validation_cap}
            ):
                _fail(
                    "child batch history is not 64+8192 base plus promotions"
                )
            promotions += validation_draws - CHILD_VALIDATION_DRAWS
    return V075AdaptiveIncrementalAccountingV1(
        result.result_id,
        result.request.occurrence_id,
        context.context_id,
        result.request.arm,
        cold,
        child_rows,
        len(child_rows) * CHILD_ROW_INITIAL_DRAWS,
        promotions,
        len(child_rows) * CHILD_ROW_INITIAL_DRAWS + promotions,
        caps.maximum_new_child_action_rows,
        caps.maximum_incremental_draws_per_adaptive_arm,
        caps.cap_profile_id,
    )


def _verify_failed_planner(
    *,
    batch_result: batch_native.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
) -> None:
    if (
        type(batch_result) is not batch_native.V075BatchNativeBackendResultV1
        or type(planner_result) is not planners.V075SupportPlannerResultV1
        or planner_result.route
        is not planners.V075PlannerRouteV1.ADAPTIVE_QUOTIENT
        or planner_result.graph.backend_result
        != batch_result.route_native_result
    ):
        _fail("failed planner artifact is untyped or batch-transplanted")
    replayed = planners.plan_v075_exact_h2_abstract_v1(
        planner_result.graph
    )
    if replayed != planner_result:
        _fail("failed planner artifact differs from exact semantic replay")
    if (
        planner_result.status
        not in {
            planners.V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY,
            planners.V075PlannerStatusV1.STATISTICAL_ENVELOPE_NOT_CERTIFIED,
        }
        or planner_result.policy is None
        or planner_result.envelope is None
    ):
        _fail("round acquisition requires a typed failed diagnostic envelope")
    threshold = worker.V075WorkerThresholdProfileV1()
    if (
        planner_result.envelope.selected_failure_upper
        <= threshold.risk_tolerance
        and planner_result.envelope.normalized_regret_upper
        <= threshold.normalized_regret_tolerance
    ):
        _fail("a certified envelope cannot trigger adaptive acquisition")


def _selected_rows(
    planner_result: planners.V075SupportPlannerResultV1,
) -> tuple[
    tuple[
        planners.V075LearnedStateNodeV1,
        backend.V075StatisticalRowV1,
        planners.V075PolicyStateChoiceV1,
    ],
    ...,
]:
    assert planner_result.policy is not None
    node_by_state = {item.state_id: item for item in planner_result.graph.nodes}
    row_by_id = {
        row.row_id: row
        for node in planner_result.graph.nodes
        for row in node.rows
    }
    result = []
    seen: set[str] = set()
    for decision in planner_result.policy.decisions:
        for choice in decision.state_choices:
            node = node_by_state.get(choice.state_id)
            if node is None:
                _fail("diagnostic policy references an absent state node")
            for row_id in choice.row_ids:
                row = row_by_id.get(row_id)
                if row is None or row_id in seen:
                    _fail("diagnostic policy row is absent or duplicated")
                seen.add(row_id)
                result.append((node, row, choice))
    if (
        planner_result.status
        is planners.V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY
        and set(planner_result.diagnostic_failed_frontier_row_ids) != seen
    ):
        _fail("diagnostic policy and failed frontier row registry disagree")
    return tuple(sorted(result, key=lambda item: item[1].row_id))


def _interval_uncertainty(row: backend.V075StatisticalRowV1) -> Fraction:
    return sum(
        (
            item.upper_probability - item.lower_probability
            for item in row.intervals
        ),
        Fraction(0),
    )


def _latest_validation_prefix(
    *,
    batch_result: batch_native.V075BatchNativeBackendResultV1,
    row_binding_id: str,
) -> tuple[public_graph.V075TransitionStreamIdentityV1, int, int]:
    values = tuple(
        item
        for item in batch_result.request.batches
        if (
            item.request.stream_identity.row_binding_id == row_binding_id
            and item.request.stream_identity.lane
            is public_graph.V075ObservationLaneV1.VALIDATION
        )
    )
    if not values:
        _fail("selected row has no validation prefix")
    epochs = {
        item.request.stream_identity.observer_epoch_index for item in values
    }
    latest_epoch = max(epochs)
    latest = tuple(
        item
        for item in values
        if item.request.stream_identity.observer_epoch_index == latest_epoch
    )
    stream_ids = {
        item.request.stream_identity.stream_id for item in latest
    }
    if len(stream_ids) != 1:
        _fail("selected row has multiple latest validation streams")
    ordered = tuple(
        sorted(latest, key=lambda item: item.request.accepted_draw_start)
    )
    expected = 1
    accepted_caps = set()
    for item in ordered:
        if item.request.accepted_draw_start != expected:
            _fail("selected validation prefix is gapped or reordered")
        expected = item.request.accepted_draw_end + 1
        accepted_caps.add(item.request.accepted_draw_cap)
    if len(accepted_caps) != 1:
        _fail("selected validation stream changed its frozen cap")
    return (
        ordered[0].request.stream_identity,
        expected - 1,
        next(iter(accepted_caps)),
    )


def _prior_numbers(
    *,
    source_view: proposal.V075SourceProposalViewV1,
    feature_key: str,
) -> tuple[
    proposal.V075PriorDispositionV1,
    Fraction | None,
    Fraction,
    Fraction,
]:
    # This private helper is the single proposal-only numerical boundary.
    return proposal._prior_fields(
        source_view=source_view,
        feature_key=feature_key,
    )


@dataclass(frozen=True, slots=True)
class V075AdaptiveRoundBundleCandidateV1:
    _issuer: object = field(repr=False, compare=False)
    batch_result_id: str
    planner_result_id: str
    failed_envelope_id: str
    accounting_id: str
    source_view_id: str
    arm: worker.V075WorkerArmV1
    round_index: int
    kind: V075BundleCandidateKindV1
    source_row_id: str
    source_row_binding: public_graph.V075ObservationRowBindingV1
    source_stream_id: str
    source_observer_epoch_index: int
    source_current_validation_draws: int
    source_validation_draw_cap: int
    child_catalogue: public_graph.V075LegalActionCatalogueV1 | None
    feature: proposal.V075PortableAcquisitionCoreFeatureReplayV2
    prior_disposition: proposal.V075PriorDispositionV1
    source_mean_midrank: Fraction | None
    applied_midrank: Fraction
    prior_multiplier: Fraction
    uncertainty_width: Fraction
    new_child_action_row_ids: tuple[str, ...]
    new_child_action_row_count: int
    root_promotion_included: bool
    incremental_draw_count: int
    base_priority: Fraction
    ranking_score: Fraction
    cap_eligible: bool

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("round-bundle candidates are compiler-issued only")
        for value, name in (
            (self.batch_result_id, "candidate batch result"),
            (self.planner_result_id, "candidate planner result"),
            (self.failed_envelope_id, "candidate failed envelope"),
            (self.accounting_id, "candidate accounting"),
            (self.source_view_id, "candidate source view"),
            (self.source_row_id, "candidate source row"),
            (self.source_stream_id, "candidate source stream"),
        ):
            _cid(value, name)
        if (
            type(self.source_row_binding)
            is not public_graph.V075ObservationRowBindingV1
        ):
            _fail("candidate source row binding is not typed")
        if (
            self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.round_index not in (1, 2)
            or type(self.kind) is not V075BundleCandidateKindV1
            or self.source_observer_epoch_index <= 0
            or self.source_current_validation_draws <= 0
            or self.source_validation_draw_cap <= 0
            or type(self.feature)
            is not proposal.V075PortableAcquisitionCoreFeatureReplayV2
            or type(self.prior_disposition)
            is not proposal.V075PriorDispositionV1
            or type(self.applied_midrank) is not Fraction
            or not 0 <= self.applied_midrank <= 1
            or type(self.prior_multiplier) is not Fraction
            or type(self.new_child_action_row_ids) is not tuple
            or self.new_child_action_row_ids
            != tuple(sorted(set(self.new_child_action_row_ids)))
            or type(self.uncertainty_width) is not Fraction
            or self.uncertainty_width <= 0
            or type(self.root_promotion_included) is not bool
            or type(self.incremental_draw_count) is not int
            or self.incremental_draw_count <= 0
            or type(self.base_priority) is not Fraction
            or self.base_priority
            != self.uncertainty_width / self.incremental_draw_count
            or type(self.ranking_score) is not Fraction
            or self.ranking_score != self.base_priority * self.prior_multiplier
            or type(self.cap_eligible) is not bool
        ):
            _fail("round-bundle candidate is malformed")
        applied = self.prior_disposition in {
            proposal.V075PriorDispositionV1.SOURCE_APPLIED,
            proposal.V075PriorDispositionV1.WRONG_REVERSED_APPLIED,
        }
        if self.source_mean_midrank is not None and (
            type(self.source_mean_midrank) is not Fraction
            or not 0 <= self.source_mean_midrank <= 1
        ):
            _fail("candidate source midrank is malformed")
        expected_dispositions = {
            worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR: {
                proposal.V075PriorDispositionV1.SOURCE_APPLIED,
                proposal.V075PriorDispositionV1.SOURCE_FEATURE_NO_MATCH_NEUTRAL,
            },
            worker.V075WorkerArmV1.WRONG_CONSENSUS_PRIOR: {
                proposal.V075PriorDispositionV1.WRONG_REVERSED_APPLIED,
                proposal.V075PriorDispositionV1.WRONG_FEATURE_NO_MATCH_NEUTRAL,
            },
            worker.V075WorkerArmV1.NO_PRIOR: {
                proposal.V075PriorDispositionV1.NO_PRIOR_NEUTRAL,
            },
            worker.V075WorkerArmV1.OOD_ABSTENTION: {
                proposal.V075PriorDispositionV1.OOD_SCHEMA_ABSTAINED,
            },
        }
        if (
            self.prior_disposition
            not in expected_dispositions.get(self.arm, set())
            or applied != (self.source_mean_midrank is not None)
            or (
                not applied
                and (
                    self.applied_midrank != 1
                    or self.prior_multiplier != 1
                )
            )
            or (
                applied
                and self.prior_multiplier
                != Fraction(1, 2)
                + Fraction(3, 2) * self.applied_midrank
            )
            or (
                self.prior_disposition
                is proposal.V075PriorDispositionV1.SOURCE_APPLIED
                and self.applied_midrank != self.source_mean_midrank
            )
            or (
                self.prior_disposition
                is proposal.V075PriorDispositionV1.WRONG_REVERSED_APPLIED
                and self.applied_midrank != 1 - self.source_mean_midrank
            )
        ):
            _fail("candidate prior disposition and source number disagree")
        for row_id in self.new_child_action_row_ids:
            _cid(row_id, "candidate new child row")
        promotion_cost = PROMOTION_DRAWS if self.root_promotion_included else 0
        if self.kind is V075BundleCandidateKindV1.MISSING_CHILD_COMPLETE_CATALOGUE:
            expected_child_rows = (
                ()
                if self.child_catalogue is None
                else tuple(
                    sorted(
                        public_graph.observation_row_binding_v1(
                            self.child_catalogue.context,
                            self.child_catalogue,
                            action,
                        ).row_binding_id
                        for action in self.child_catalogue.actions
                    )
                )
            )
            if (
                type(self.child_catalogue)
                is not public_graph.V075LegalActionCatalogueV1
                or self.child_catalogue.remaining_horizon != 1
                or self.child_catalogue.context
                != self.source_row_binding.context
                or self.new_child_action_row_ids != expected_child_rows
                or self.new_child_action_row_count
                != len(self.new_child_action_row_ids)
                or self.new_child_action_row_count <= 0
                or self.incremental_draw_count
                != (
                    self.new_child_action_row_count
                    * CHILD_ROW_INITIAL_DRAWS
                    + promotion_cost
                )
            ):
                _fail("missing-child candidate lacks its complete catalogue cost")
        elif (
            self.child_catalogue is not None
            or self.new_child_action_row_ids
            or self.new_child_action_row_count != 0
            or not self.root_promotion_included
            or self.incremental_draw_count != PROMOTION_DRAWS
        ):
            _fail("promotion candidate contains child materialization work")

    @property
    def source_row_binding_id(self) -> str:
        return self.source_row_binding.row_binding_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_round_bundle_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "batch_result_id": self.batch_result_id,
            "planner_result_id": self.planner_result_id,
            "failed_envelope_id": self.failed_envelope_id,
            "accounting_id": self.accounting_id,
            "source_view_id": self.source_view_id,
            "arm": self.arm.value,
            "round_index": self.round_index,
            "kind": self.kind.value,
            "source_row_id": self.source_row_id,
            "source_row_binding_id": self.source_row_binding_id,
            "source_stream_id": self.source_stream_id,
            "source_observer_epoch_index": (
                self.source_observer_epoch_index
            ),
            "source_current_validation_draws": (
                self.source_current_validation_draws
            ),
            "source_validation_draw_cap": self.source_validation_draw_cap,
            "child_catalogue_id": (
                None
                if self.child_catalogue is None
                else self.child_catalogue.catalogue_id
            ),
            "feature_key": self.feature.feature_key,
            "prior_disposition": self.prior_disposition.value,
            "source_mean_midrank": (
                None
                if self.source_mean_midrank is None
                else _fdoc(self.source_mean_midrank)
            ),
            "applied_midrank": _fdoc(self.applied_midrank),
            "prior_multiplier": _fdoc(self.prior_multiplier),
            "uncertainty_width": _fdoc(self.uncertainty_width),
            "new_child_action_row_ids": list(
                self.new_child_action_row_ids
            ),
            "new_child_action_row_count": self.new_child_action_row_count,
            "root_promotion_included": self.root_promotion_included,
            "incremental_draw_count": self.incremental_draw_count,
            "base_priority": _fdoc(self.base_priority),
            "ranking_score": _fdoc(self.ranking_score),
            "cap_eligible": self.cap_eligible,
            "proposal_only": True,
            "prior_changes_model_or_certificate": False,
        }

    @property
    def candidate_id(self) -> str:
        return _hash("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "child_catalogue": (
                None
                if self.child_catalogue is None
                else self.child_catalogue.to_document()
            ),
            "source_row_binding": self.source_row_binding.to_document(),
            "feature": self.feature.to_document(),
            "candidate_id": self.candidate_id,
        }


@dataclass(frozen=True, slots=True)
class V075AdaptiveRoundBundleFrontierV1:
    batch_result_id: str
    planner_result_id: str
    failed_envelope_id: str
    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    round_index: int
    source_view: proposal.V075SourceProposalViewV1
    accounting: V075AdaptiveIncrementalAccountingV1
    candidates: tuple[V075AdaptiveRoundBundleCandidateV1, ...]
    ranked_candidate_ids: tuple[str, ...]
    preproposal_batch_ids: tuple[str, ...]
    previous_execution_id: str | None

    def __post_init__(self) -> None:
        for value, name in (
            (self.batch_result_id, "frontier batch result"),
            (self.planner_result_id, "frontier planner result"),
            (self.failed_envelope_id, "frontier failed envelope"),
            (self.occurrence_id, "frontier occurrence"),
            (self.context_id, "frontier context"),
        ):
            _cid(value, name)
        if self.previous_execution_id is not None:
            _cid(self.previous_execution_id, "frontier previous execution")
        if (
            self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.round_index not in (1, 2)
            or type(self.source_view) is not proposal.V075SourceProposalViewV1
            or self.source_view.arm is not self.arm
            or type(self.accounting) is not V075AdaptiveIncrementalAccountingV1
            or self.accounting.batch_result_id != self.batch_result_id
            or self.accounting.occurrence_id != self.occurrence_id
            or self.accounting.context_id != self.context_id
            or self.accounting.arm is not self.arm
            or self.candidates
            != tuple(sorted(self.candidates, key=lambda item: item.candidate_id))
            or len({item.candidate_id for item in self.candidates})
            != len(self.candidates)
            or self.ranked_candidate_ids
            != tuple(
                item.candidate_id
                for item in sorted(
                    self.candidates,
                    key=lambda item: (
                        -item.ranking_score,
                        -item.base_priority,
                        item.candidate_id,
                    ),
                )
            )
            or self.preproposal_batch_ids
            != tuple(sorted(set(self.preproposal_batch_ids)))
            or (self.round_index == 1) != (self.previous_execution_id is None)
        ):
            _fail("round-bundle frontier is malformed or reordered")
        if any(
            item.batch_result_id != self.batch_result_id
            or item.planner_result_id != self.planner_result_id
            or item.failed_envelope_id != self.failed_envelope_id
            or item.accounting_id != self.accounting.accounting_id
            or item.source_view_id != self.source_view.source_view_id
            or item.arm is not self.arm
            or item.round_index != self.round_index
            or item.source_row_binding.context_id != self.context_id
            for item in self.candidates
        ):
            _fail("frontier contains a transplanted bundle candidate")
        accounted_child_rows = set(self.accounting.new_child_action_row_ids)
        for item in self.candidates:
            new_rows = set(item.new_child_action_row_ids)
            if (
                new_rows & accounted_child_rows
                or item.cap_eligible
                != (
                    self.accounting.incremental_draws_used
                    + item.incremental_draw_count
                    <= self.accounting.maximum_incremental_draws
                    and len(accounted_child_rows | new_rows)
                    <= self.accounting.maximum_new_child_action_rows
                    and (
                        not item.root_promotion_included
                        or item.source_current_validation_draws
                        + PROMOTION_DRAWS
                        <= item.source_validation_draw_cap
                    )
                )
            ):
                _fail("candidate cap eligibility differs from exact union replay")
        kinds = {item.kind for item in self.candidates}
        if (
            V075BundleCandidateKindV1.MISSING_CHILD_COMPLETE_CATALOGUE
            in kinds
            and kinds
            != {
                V075BundleCandidateKindV1.MISSING_CHILD_COMPLETE_CATALOGUE
            }
        ):
            _fail("missing-child frontier cannot mix pure promotions")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_round_bundle_frontier.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "batch_result_id": self.batch_result_id,
            "planner_result_id": self.planner_result_id,
            "failed_envelope_id": self.failed_envelope_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "round_index": self.round_index,
            "source_view_id": self.source_view.source_view_id,
            "accounting_id": self.accounting.accounting_id,
            "candidate_ids": [item.candidate_id for item in self.candidates],
            "ranked_candidate_ids": list(self.ranked_candidate_ids),
            "preproposal_batch_ids": list(self.preproposal_batch_ids),
            "previous_execution_id": self.previous_execution_id,
            "missing_child_candidates_exclude_pure_promotions": True,
            "frozen_before_target_access": True,
            "observer_calls": 0,
            "kernel_calls": 0,
        }

    @property
    def frontier_id(self) -> str:
        return _hash("frontier", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_view": self.source_view.to_document(),
            "accounting": self.accounting.to_document(),
            "candidates": [item.to_document() for item in self.candidates],
            "frontier_id": self.frontier_id,
        }


@dataclass(frozen=True, slots=True)
class V075AdaptiveRoundBundleRowIntentV1:
    _issuer: object = field(repr=False, compare=False)
    frontier_id: str
    candidate_id: str
    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    round_index: int
    kind: V075BundleIntentKindV1
    row_binding: public_graph.V075ObservationRowBindingV1
    observer_epoch_index: int
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_cap: int
    existing_stream_id: str | None
    dependency_intent_id: str | None

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("round-bundle row intents are compiler-issued only")
        for value, name in (
            (self.frontier_id, "intent frontier"),
            (self.candidate_id, "intent candidate"),
            (self.occurrence_id, "intent occurrence"),
            (self.context_id, "intent context"),
        ):
            _cid(value, name)
        if self.existing_stream_id is not None:
            _cid(self.existing_stream_id, "intent existing stream")
        if self.dependency_intent_id is not None:
            _cid(self.dependency_intent_id, "intent dependency")
        if (
            self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.round_index not in (1, 2)
            or type(self.kind) is not V075BundleIntentKindV1
            or type(self.row_binding)
            is not public_graph.V075ObservationRowBindingV1
            or self.row_binding.context_id != self.context_id
        ):
            _fail("round-bundle row intent is malformed")
        if self.kind is V075BundleIntentKindV1.EXISTING_VALIDATION_PREFIX_EXTENSION:
            if (
                self.existing_stream_id is None
                or self.dependency_intent_id is not None
                or self.observer_epoch_index <= 0
                or self.accepted_draw_start <= 1
                or self.accepted_draw_count != PROMOTION_DRAWS
                or self.accepted_draw_end > self.accepted_draw_cap
            ):
                _fail("existing validation extension intent is invalid")
        elif self.kind is V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY:
            if (
                self.existing_stream_id is not None
                or self.dependency_intent_id is not None
                or self.observer_epoch_index != 0
                or self.accepted_draw_start != 1
                or self.accepted_draw_count != CHILD_DISCOVERY_DRAWS
                or self.accepted_draw_cap != CHILD_DISCOVERY_DRAWS
            ):
                _fail("new child discovery intent is invalid")
        elif (
            self.existing_stream_id is not None
            or self.dependency_intent_id is None
            or self.observer_epoch_index != 1
            or self.accepted_draw_start != 1
            or self.accepted_draw_count != CHILD_VALIDATION_DRAWS
            or self.accepted_draw_cap != CHILD_VALIDATION_ACCEPTED_DRAW_CAP
        ):
            _fail("new child validation intent is invalid")

    @property
    def accepted_draw_end(self) -> int:
        return self.accepted_draw_start + self.accepted_draw_count - 1

    @property
    def lane(self) -> public_graph.V075ObservationLaneV1:
        return (
            public_graph.V075ObservationLaneV1.DISCOVERY
            if self.kind is V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
            else public_graph.V075ObservationLaneV1.VALIDATION
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_round_bundle_row_intent.v1",
            "schema_version": SCHEMA_VERSION,
            "frontier_id": self.frontier_id,
            "candidate_id": self.candidate_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "round_index": self.round_index,
            "kind": self.kind.value,
            "row_binding_id": self.row_binding.row_binding_id,
            "catalogue_id": self.row_binding.catalogue_id,
            "action": list(self.row_binding.action),
            "lane": self.lane.value,
            "observer_epoch_index": self.observer_epoch_index,
            "accepted_draw_start": self.accepted_draw_start,
            "accepted_draw_count": self.accepted_draw_count,
            "accepted_draw_end": self.accepted_draw_end,
            "accepted_draw_cap": self.accepted_draw_cap,
            "existing_stream_id": self.existing_stream_id,
            "dependency_intent_id": self.dependency_intent_id,
            "aggregate_support_freeze_required_before_validation": (
                self.kind
                is V075BundleIntentKindV1.NEW_CHILD_ROW_VALIDATION
            ),
            "observer_calls": 0,
            "kernel_calls": 0,
        }

    @property
    def intent_id(self) -> str:
        return _hash("intent", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding": self.row_binding.to_document(),
            "intent_id": self.intent_id,
        }


@dataclass(frozen=True, slots=True)
class V075AdaptiveRoundBundleAuthorizationV1:
    frontier: V075AdaptiveRoundBundleFrontierV1
    status: V075BundleAuthorizationStatusV1
    selected_candidate_id: str | None
    intents: tuple[V075AdaptiveRoundBundleRowIntentV1, ...]
    authorization_sequence: int
    minimum_observer_sequence: int

    def __post_init__(self) -> None:
        if (
            type(self.frontier) is not V075AdaptiveRoundBundleFrontierV1
            or type(self.status) is not V075BundleAuthorizationStatusV1
            or type(self.intents) is not tuple
            or self.authorization_sequence != 2 * self.frontier.round_index - 1
            or self.minimum_observer_sequence != self.authorization_sequence + 1
        ):
            _fail("round-bundle authorization is malformed")
        authorized = self.status is V075BundleAuthorizationStatusV1.AUTHORIZED
        if authorized:
            candidate_by_id = {
                item.candidate_id: item for item in self.frontier.candidates
            }
            selected = candidate_by_id.get(self.selected_candidate_id)
            eligible = tuple(
                item
                for item in sorted(
                    self.frontier.candidates,
                    key=lambda value: (
                        -value.ranking_score,
                        -value.base_priority,
                        value.candidate_id,
                    ),
                )
                if item.cap_eligible
            )
            if (
                selected is None
                or not eligible
                or selected != eligible[0]
                or not self.intents
                or any(
                    item.frontier_id != self.frontier.frontier_id
                    or item.candidate_id != selected.candidate_id
                    or item.occurrence_id != self.frontier.occurrence_id
                    or item.context_id != self.frontier.context_id
                    or item.arm is not self.frontier.arm
                    or item.round_index != self.frontier.round_index
                    for item in self.intents
                )
                or sum(item.accepted_draw_count for item in self.intents)
                != selected.incremental_draw_count
            ):
                _fail("authorization does not execute the first eligible bundle")
            discoveries = tuple(
                item for item in self.intents
                if item.kind is V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
            )
            extensions = tuple(
                item
                for item in self.intents
                if item.kind
                is V075BundleIntentKindV1
                .EXISTING_VALIDATION_PREFIX_EXTENSION
            )
            validations = tuple(
                item for item in self.intents
                if item.kind is V075BundleIntentKindV1.NEW_CHILD_ROW_VALIDATION
            )
            if self.intents != (*discoveries, *extensions, *validations):
                _fail(
                    "authorized intent registry violates the discovery, "
                    "support-barrier, validation phase order"
                )
            if selected.kind is V075BundleCandidateKindV1.MISSING_CHILD_COMPLETE_CATALOGUE:
                assert selected.child_catalogue is not None
                expected_rows = tuple(
                    public_graph.observation_row_binding_v1(
                        selected.child_catalogue.context,
                        selected.child_catalogue,
                        action,
                    ).row_binding_id
                    for action in selected.child_catalogue.actions
                )
                if (
                    tuple(item.row_binding.row_binding_id for item in discoveries)
                    != expected_rows
                    or tuple(item.row_binding.row_binding_id for item in validations)
                    != expected_rows
                    or tuple(item.dependency_intent_id for item in validations)
                    != tuple(item.intent_id for item in discoveries)
                ):
                    _fail("authorized child bundle omitted its complete catalogue")
            elif discoveries or validations or len(self.intents) != 1:
                _fail("pure promotion authorization contains child intents")
        elif self.selected_candidate_id is not None or self.intents:
            _fail("nonauthorization cannot contain target row intents")
        if (
            self.status
            is V075BundleAuthorizationStatusV1.NO_UNCERTAIN_PROOF_FRONTIER
        ) != (not self.frontier.candidates):
            _fail("no-frontier status disagrees with candidate registry")
        if (
            self.status
            is V075BundleAuthorizationStatusV1.INCREMENTAL_CAP_EXHAUSTED
            and (
                not self.frontier.candidates
                or any(item.cap_eligible for item in self.frontier.candidates)
            )
        ):
            _fail("cap-exhausted status has an eligible bundle")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_round_bundle_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "frontier_id": self.frontier.frontier_id,
            "status": self.status.value,
            "selected_candidate_id": self.selected_candidate_id,
            "intent_ids": [item.intent_id for item in self.intents],
            "authorization_sequence": self.authorization_sequence,
            "minimum_observer_sequence": self.minimum_observer_sequence,
            "observer_execution_phase_order": [
                "NEW_CHILD_DISCOVERY",
                "SUPPORT_FREEZE_REGISTER_BARRIER",
                "EXISTING_VALIDATION_PREFIX_EXTENSION",
                "NEW_CHILD_VALIDATION",
            ],
            "support_freeze_register_barrier_after_intent_ids": [
                item.intent_id
                for item in self.intents
                if item.kind
                is V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY
            ],
            "frozen_before_target_access": True,
            "observer_calls": 0,
            "kernel_calls": 0,
        }

    @property
    def authorization_id(self) -> str:
        return _hash("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "frontier": self.frontier.to_document(),
            "intents": [item.to_document() for item in self.intents],
            "authorization_id": self.authorization_id,
        }


@dataclass(frozen=True, slots=True)
class V075AdaptiveRoundBundleExecutionV1:
    authorization_id: str
    prior_batch_result_id: str
    resulting_batch_result_id: str
    executed_intent_ids: tuple[str, ...]
    appended_batch_ids: tuple[str, ...]
    resulting_accounting: V075AdaptiveIncrementalAccountingV1
    exact_append_only_execution: bool = True

    def __post_init__(self) -> None:
        for value, name in (
            (self.authorization_id, "execution authorization"),
            (self.prior_batch_result_id, "execution prior result"),
            (self.resulting_batch_result_id, "execution resulting result"),
        ):
            _cid(value, name)
        if (
            type(self.executed_intent_ids) is not tuple
            or not self.executed_intent_ids
            or len(set(self.executed_intent_ids))
            != len(self.executed_intent_ids)
            or type(self.appended_batch_ids) is not tuple
            or self.appended_batch_ids
            != tuple(sorted(set(self.appended_batch_ids)))
            or not self.appended_batch_ids
            or type(self.resulting_accounting)
            is not V075AdaptiveIncrementalAccountingV1
            or self.resulting_accounting.batch_result_id
            != self.resulting_batch_result_id
            or self.exact_append_only_execution is not True
        ):
            _fail("round-bundle execution verification is malformed")
        for item in (*self.executed_intent_ids, *self.appended_batch_ids):
            _cid(item, "executed bundle member")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_adaptive_round_bundle_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "authorization_id": self.authorization_id,
            "prior_batch_result_id": self.prior_batch_result_id,
            "resulting_batch_result_id": self.resulting_batch_result_id,
            "executed_intent_ids": list(self.executed_intent_ids),
            "appended_batch_ids": list(self.appended_batch_ids),
            "resulting_accounting_id": (
                self.resulting_accounting.accounting_id
            ),
            "exact_append_only_execution": True,
            "post_run_reorder_allowed": False,
        }

    @property
    def execution_id(self) -> str:
        return _hash("execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "resulting_accounting": self.resulting_accounting.to_document(),
            "execution_id": self.execution_id,
        }


def _candidate_common(
    *,
    batch_result: batch_native.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
    accounting: V075AdaptiveIncrementalAccountingV1,
    source_view: proposal.V075SourceProposalViewV1,
    round_index: int,
    node: planners.V075LearnedStateNodeV1,
    row: backend.V075StatisticalRowV1,
    choice: planners.V075PolicyStateChoiceV1,
) -> tuple[
    proposal.V075PortableAcquisitionCoreFeatureReplayV2,
    proposal.V075PriorDispositionV1,
    Fraction | None,
    Fraction,
    Fraction,
    Fraction,
    public_graph.V075TransitionStreamIdentityV1,
    int,
    int,
]:
    feature = proposal.replay_v075_target_portable_feature_v2(
        node=node,
        row=row,
        choice=choice,
    )
    disposition, source_q, applied_q, multiplier = _prior_numbers(
        source_view=source_view,
        feature_key=feature.feature_key,
    )
    width = _interval_uncertainty(row)
    stream, count, cap = _latest_validation_prefix(
        batch_result=batch_result,
        row_binding_id=row.row_binding_id,
    )
    return (
        feature,
        disposition,
        source_q,
        applied_q,
        multiplier,
        width,
        stream,
        count,
        cap,
    )


def _typed_source_row_binding(
    *,
    node: planners.V075LearnedStateNodeV1,
    row: backend.V075StatisticalRowV1,
) -> public_graph.V075ObservationRowBindingV1:
    binding = public_graph.observation_row_binding_v1(
        node.catalogue.context,
        node.catalogue,
        row.action,
    )
    if binding.row_binding_id != row.row_binding_id:
        _fail("planner row differs from its reconstructed typed row binding")
    return binding


def _child_candidates(
    *,
    batch_result: batch_native.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
    accounting: V075AdaptiveIncrementalAccountingV1,
    source_view: proposal.V075SourceProposalViewV1,
    round_index: int,
) -> tuple[V075AdaptiveRoundBundleCandidateV1, ...]:
    context = batch_result.request.context
    materialized_states = {
        item.state_id for item in planner_result.graph.nodes
    }
    candidates: list[V075AdaptiveRoundBundleCandidateV1] = []
    for node, row, choice in _selected_rows(planner_result):
        if row.remaining_horizon != 2:
            continue
        (
            feature,
            disposition,
            source_q,
            applied_q,
            multiplier,
            width,
            stream,
            current_count,
            stream_cap,
        ) = _candidate_common(
            batch_result=batch_result,
            planner_result=planner_result,
            accounting=accounting,
            source_view=source_view,
            round_index=round_index,
            node=node,
            row=row,
            choice=choice,
        )
        source_binding = _typed_source_row_binding(node=node, row=row)
        if width <= 0:
            continue
        for descriptor in row.support:
            if (
                descriptor.failure
                or descriptor.terminal
                or descriptor.next_state_id in materialized_states
            ):
                continue
            try:
                child_state = public_graph.V075SymbolicGraphStateV1(
                    context,
                    descriptor.next_ranks,
                    descriptor.failure,
                )
                child_catalogue = public_graph.V075LegalActionCatalogueV1(
                    context,
                    child_state,
                    1,
                    public_graph.legal_action_triples_v1(
                        context,
                        child_state.ranks,
                        child_state.failure,
                    ),
                )
            except public_graph.V075PublicGraphSemanticsInvariantViolation as error:
                raise V075AdaptiveRoundBundleInvariantViolation(
                    str(error)
                ) from error
            if not child_catalogue.actions:
                _fail("active missing child has an empty legal-action catalogue")
            child_row_ids = tuple(
                sorted(
                    public_graph.observation_row_binding_v1(
                        context,
                        child_catalogue,
                        action,
                    ).row_binding_id
                    for action in child_catalogue.actions
                )
            )
            if set(child_row_ids) & set(
                accounting.new_child_action_row_ids
            ):
                _fail("missing child candidate reuses a materialized child row")
            include_promotion = current_count + PROMOTION_DRAWS <= stream_cap
            cost = (
                len(child_row_ids) * CHILD_ROW_INITIAL_DRAWS
                + (PROMOTION_DRAWS if include_promotion else 0)
            )
            cap_eligible = (
                accounting.incremental_draws_used + cost
                <= accounting.maximum_incremental_draws
                and len(
                    set(accounting.new_child_action_row_ids)
                    | set(child_row_ids)
                )
                <= accounting.maximum_new_child_action_rows
            )
            base = width / cost
            candidates.append(
                V075AdaptiveRoundBundleCandidateV1(
                    _ISSUER,
                    batch_result.result_id,
                    planner_result.result_id,
                    planner_result.envelope.envelope_id,
                    accounting.accounting_id,
                    source_view.source_view_id,
                    source_view.arm,
                    round_index,
                    V075BundleCandidateKindV1.MISSING_CHILD_COMPLETE_CATALOGUE,
                    row.row_id,
                    source_binding,
                    stream.stream_id,
                    stream.observer_epoch_index,
                    current_count,
                    stream_cap,
                    child_catalogue,
                    feature,
                    disposition,
                    source_q,
                    applied_q,
                    multiplier,
                    width,
                    child_row_ids,
                    len(child_row_ids),
                    include_promotion,
                    cost,
                    base,
                    base * multiplier,
                    cap_eligible,
                )
            )
    # One child state is one acquisition candidate even if multiple selected
    # concretizer rows observed it.  Keep the deterministic highest score.
    by_child: dict[str, V075AdaptiveRoundBundleCandidateV1] = {}
    for item in candidates:
        assert item.child_catalogue is not None
        key = item.child_catalogue.state.state_id
        prior = by_child.get(key)
        if prior is None or (
            -item.ranking_score,
            -item.base_priority,
            item.candidate_id,
        ) < (
            -prior.ranking_score,
            -prior.base_priority,
            prior.candidate_id,
        ):
            by_child[key] = item
    return tuple(sorted(by_child.values(), key=lambda item: item.candidate_id))


def _promotion_candidates(
    *,
    batch_result: batch_native.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
    accounting: V075AdaptiveIncrementalAccountingV1,
    source_view: proposal.V075SourceProposalViewV1,
    round_index: int,
) -> tuple[V075AdaptiveRoundBundleCandidateV1, ...]:
    result = []
    for node, row, choice in _selected_rows(planner_result):
        (
            feature,
            disposition,
            source_q,
            applied_q,
            multiplier,
            width,
            stream,
            current_count,
            stream_cap,
        ) = _candidate_common(
            batch_result=batch_result,
            planner_result=planner_result,
            accounting=accounting,
            source_view=source_view,
            round_index=round_index,
            node=node,
            row=row,
            choice=choice,
        )
        source_binding = _typed_source_row_binding(node=node, row=row)
        if width <= 0:
            continue
        cap_eligible = (
            current_count + PROMOTION_DRAWS <= stream_cap
            and accounting.incremental_draws_used + PROMOTION_DRAWS
            <= accounting.maximum_incremental_draws
        )
        base = width / PROMOTION_DRAWS
        result.append(
            V075AdaptiveRoundBundleCandidateV1(
                _ISSUER,
                batch_result.result_id,
                planner_result.result_id,
                planner_result.envelope.envelope_id,
                accounting.accounting_id,
                source_view.source_view_id,
                source_view.arm,
                round_index,
                V075BundleCandidateKindV1.SELECTED_ROW_VALIDATION_PROMOTION,
                row.row_id,
                source_binding,
                stream.stream_id,
                stream.observer_epoch_index,
                current_count,
                stream_cap,
                None,
                feature,
                disposition,
                source_q,
                applied_q,
                multiplier,
                width,
                (),
                0,
                True,
                PROMOTION_DRAWS,
                base,
                base * multiplier,
                cap_eligible,
            )
        )
    return tuple(sorted(result, key=lambda item: item.candidate_id))


def freeze_v075_adaptive_round_bundle_frontier_v1(
    *,
    batch_result: batch_native.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
    source_view: proposal.V075SourceProposalViewV1,
    round_index: int,
    previous_execution: V075AdaptiveRoundBundleExecutionV1 | None = None,
) -> V075AdaptiveRoundBundleFrontierV1:
    """Freeze one law-free failed-proof acquisition frontier."""

    if round_index not in (1, 2):
        _fail("round index exceeds the registered two-round cap")
    _verify_failed_planner(
        batch_result=batch_result,
        planner_result=planner_result,
    )
    if (
        type(source_view) is not proposal.V075SourceProposalViewV1
        or source_view.arm is not batch_result.request.arm
    ):
        _fail("source view and batch-native arm disagree")
    accounting = replay_v075_incremental_accounting_v1(batch_result)
    if round_index == 1:
        if previous_execution is not None:
            _fail("round one cannot consume a previous execution")
        if (
            accounting.incremental_draws_used != 0
            or accounting.new_child_action_row_ids
        ):
            _fail("fresh round one must begin after root-only cold acquisition")
        previous_id = None
    else:
        if (
            type(previous_execution) is not V075AdaptiveRoundBundleExecutionV1
            or previous_execution.resulting_batch_result_id
            != batch_result.result_id
            or previous_execution.resulting_accounting != accounting
        ):
            _fail("round two lacks exact append-only round-one execution")
        previous_id = previous_execution.execution_id
    children = _child_candidates(
        batch_result=batch_result,
        planner_result=planner_result,
        accounting=accounting,
        source_view=source_view,
        round_index=round_index,
    )
    candidates = (
        children
        if children
        else _promotion_candidates(
            batch_result=batch_result,
            planner_result=planner_result,
            accounting=accounting,
            source_view=source_view,
            round_index=round_index,
        )
    )
    ranked = tuple(
        item.candidate_id
        for item in sorted(
            candidates,
            key=lambda item: (
                -item.ranking_score,
                -item.base_priority,
                item.candidate_id,
            ),
        )
    )
    return V075AdaptiveRoundBundleFrontierV1(
        batch_result.result_id,
        planner_result.result_id,
        planner_result.envelope.envelope_id,
        batch_result.request.occurrence_id,
        batch_result.request.context.context_id,
        source_view.arm,
        round_index,
        source_view,
        accounting,
        candidates,
        ranked,
        tuple(sorted(item.batch_id for item in batch_result.request.batches)),
        previous_id,
    )


def _extension_intent(
    *,
    frontier: V075AdaptiveRoundBundleFrontierV1,
    candidate: V075AdaptiveRoundBundleCandidateV1,
    row_binding: public_graph.V075ObservationRowBindingV1,
) -> V075AdaptiveRoundBundleRowIntentV1:
    return V075AdaptiveRoundBundleRowIntentV1(
        _ISSUER,
        frontier.frontier_id,
        candidate.candidate_id,
        frontier.occurrence_id,
        frontier.context_id,
        frontier.arm,
        frontier.round_index,
        V075BundleIntentKindV1.EXISTING_VALIDATION_PREFIX_EXTENSION,
        row_binding,
        candidate.source_observer_epoch_index,
        candidate.source_current_validation_draws + 1,
        PROMOTION_DRAWS,
        candidate.source_validation_draw_cap,
        candidate.source_stream_id,
        None,
    )


def authorize_v075_adaptive_round_bundle_v1(
    frontier: V075AdaptiveRoundBundleFrontierV1,
) -> V075AdaptiveRoundBundleAuthorizationV1:
    if type(frontier) is not V075AdaptiveRoundBundleFrontierV1:
        _fail("bundle authorizer requires one exact frozen frontier")
    sequence = 2 * frontier.round_index - 1
    if not frontier.candidates:
        return V075AdaptiveRoundBundleAuthorizationV1(
            frontier,
            V075BundleAuthorizationStatusV1.NO_UNCERTAIN_PROOF_FRONTIER,
            None,
            (),
            sequence,
            sequence + 1,
        )
    eligible = tuple(
        item
        for item in sorted(
            frontier.candidates,
            key=lambda value: (
                -value.ranking_score,
                -value.base_priority,
                value.candidate_id,
            ),
        )
        if item.cap_eligible
    )
    if not eligible:
        return V075AdaptiveRoundBundleAuthorizationV1(
            frontier,
            V075BundleAuthorizationStatusV1.INCREMENTAL_CAP_EXHAUSTED,
            None,
            (),
            sequence,
            sequence + 1,
        )
    selected = eligible[0]
    context = _registered_context(frontier.context_id)
    source_binding = selected.source_row_binding
    if source_binding.context != context:
        _fail("selected source binding was transplanted across contexts")
    extensions: list[V075AdaptiveRoundBundleRowIntentV1] = []
    if selected.root_promotion_included:
        extensions.append(
            _extension_intent(
                frontier=frontier,
                candidate=selected,
                row_binding=source_binding,
            )
        )
    if selected.kind is V075BundleCandidateKindV1.MISSING_CHILD_COMPLETE_CATALOGUE:
        assert selected.child_catalogue is not None
        discoveries = []
        for action in selected.child_catalogue.actions:
            binding = public_graph.observation_row_binding_v1(
                context,
                selected.child_catalogue,
                action,
            )
            discoveries.append(
                V075AdaptiveRoundBundleRowIntentV1(
                    _ISSUER,
                    frontier.frontier_id,
                    selected.candidate_id,
                    frontier.occurrence_id,
                    frontier.context_id,
                    frontier.arm,
                    frontier.round_index,
                    V075BundleIntentKindV1.NEW_CHILD_ROW_DISCOVERY,
                    binding,
                    0,
                    1,
                    CHILD_DISCOVERY_DRAWS,
                    CHILD_DISCOVERY_DRAWS,
                    None,
                    None,
                )
            )
        validations = tuple(
            V075AdaptiveRoundBundleRowIntentV1(
                _ISSUER,
                frontier.frontier_id,
                selected.candidate_id,
                frontier.occurrence_id,
                frontier.context_id,
                frontier.arm,
                frontier.round_index,
                V075BundleIntentKindV1.NEW_CHILD_ROW_VALIDATION,
                discovery.row_binding,
                1,
                1,
                CHILD_VALIDATION_DRAWS,
                CHILD_VALIDATION_ACCEPTED_DRAW_CAP,
                None,
                discovery.intent_id,
            )
            for discovery in discoveries
        )
        intents = (*discoveries, *extensions, *validations)
    else:
        intents = tuple(extensions)
    return V075AdaptiveRoundBundleAuthorizationV1(
        frontier,
        V075BundleAuthorizationStatusV1.AUTHORIZED,
        selected.candidate_id,
        tuple(intents),
        sequence,
        sequence + 1,
    )


def _match_intent_batches(
    *,
    intent: V075AdaptiveRoundBundleRowIntentV1,
    appended: tuple[Any, ...],
) -> tuple[Any, ...]:
    values = tuple(
        sorted(
            (
                item
                for item in appended
                if (
                    item.request.stream_identity.row_binding_id
                    == intent.row_binding.row_binding_id
                    and item.request.stream_identity.lane is intent.lane
                    and item.request.stream_identity.observer_epoch_index
                    == intent.observer_epoch_index
                    and (
                        intent.existing_stream_id is None
                        or item.request.stream_identity.stream_id
                        == intent.existing_stream_id
                    )
                )
            ),
            key=lambda item: item.request.accepted_draw_start,
        )
    )
    if not values:
        _fail("authorized intent has no appended batch")
    if (
        values[0].request.accepted_draw_start != intent.accepted_draw_start
        or values[-1].request.accepted_draw_end != intent.accepted_draw_end
        or any(
            left.request.accepted_draw_end + 1
            != right.request.accepted_draw_start
            for left, right in zip(values, values[1:])
        )
        or sum(item.request.accepted_draw_count for item in values)
        != intent.accepted_draw_count
        or any(
            item.request.accepted_draw_cap != intent.accepted_draw_cap
            for item in values
        )
    ):
        _fail("appended batches do not equal the frozen intent interval")
    return values


def verify_v075_adaptive_round_bundle_execution_v1(
    *,
    authorization: V075AdaptiveRoundBundleAuthorizationV1,
    resulting_batch_result: batch_native.V075BatchNativeBackendResultV1,
) -> V075AdaptiveRoundBundleExecutionV1:
    """Verify that exactly the authorized bundle was appended."""

    if (
        type(authorization) is not V075AdaptiveRoundBundleAuthorizationV1
        or authorization.status
        is not V075BundleAuthorizationStatusV1.AUTHORIZED
        or type(resulting_batch_result)
        is not batch_native.V075BatchNativeBackendResultV1
    ):
        _fail("bundle execution verifier requires one authorized result")
    frontier = authorization.frontier
    if (
        resulting_batch_result.request.occurrence_id != frontier.occurrence_id
        or resulting_batch_result.request.context.context_id
        != frontier.context_id
        or resulting_batch_result.request.arm is not frontier.arm
    ):
        _fail("bundle execution was transplanted across occurrence or arm")
    before = set(frontier.preproposal_batch_ids)
    all_after = {
        item.batch_id for item in resulting_batch_result.request.batches
    }
    if not before < all_after:
        _fail("bundle execution did not append to its frozen batch set")
    appended = tuple(
        item
        for item in resulting_batch_result.request.batches
        if item.batch_id not in before
    )
    consumed: set[str] = set()
    for intent in authorization.intents:
        matches = _match_intent_batches(intent=intent, appended=appended)
        ids = {item.batch_id for item in matches}
        if consumed & ids:
            _fail("one appended batch was charged to multiple intents")
        consumed.update(ids)
    if consumed != {item.batch_id for item in appended}:
        _fail("post-run execution added an unauthorized row or reordered bundle")
    resulting_accounting = replay_v075_incremental_accounting_v1(
        resulting_batch_result
    )
    selected = next(
        item
        for item in frontier.candidates
        if item.candidate_id == authorization.selected_candidate_id
    )
    if (
        resulting_accounting.incremental_draws_used
        != frontier.accounting.incremental_draws_used
        + selected.incremental_draw_count
        or len(resulting_accounting.new_child_action_row_ids)
        != len(frontier.accounting.new_child_action_row_ids)
        + selected.new_child_action_row_count
    ):
        _fail("trusted replay cost differs from the authorized bundle cost")
    return V075AdaptiveRoundBundleExecutionV1(
        authorization.authorization_id,
        frontier.batch_result_id,
        resulting_batch_result.result_id,
        tuple(item.intent_id for item in authorization.intents),
        tuple(sorted(consumed)),
        resulting_accounting,
    )


__all__ = [
    "CHILD_DISCOVERY_DRAWS",
    "CHILD_ROW_INITIAL_DRAWS",
    "CHILD_VALIDATION_ACCEPTED_DRAW_CAP",
    "CHILD_VALIDATION_DRAWS",
    "MAX_ROUNDS",
    "PROFILE_KEY",
    "PROMOTION_DRAWS",
    "PRODUCTION_INTEGRATION_READY",
    "V075AdaptiveIncrementalAccountingV1",
    "V075AdaptiveRoundBundleAuthorizationV1",
    "V075AdaptiveRoundBundleCandidateV1",
    "V075AdaptiveRoundBundleExecutionV1",
    "V075AdaptiveRoundBundleFrontierV1",
    "V075AdaptiveRoundBundleInvariantViolation",
    "V075AdaptiveRoundBundleRowIntentV1",
    "V075BundleAuthorizationStatusV1",
    "V075BundleCandidateKindV1",
    "V075BundleIntentKindV1",
    "authorize_v075_adaptive_round_bundle_v1",
    "freeze_v075_adaptive_round_bundle_frontier_v1",
    "replay_v075_incremental_accounting_v1",
    "verify_v075_adaptive_round_bundle_execution_v1",
]
