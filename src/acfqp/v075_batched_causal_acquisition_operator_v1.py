"""Cap-aware batched causal acquisition for a frozen V0-075 frontier.

The frozen V1 acquisition authority ranks one missing-child catalogue per
round.  That is a useful no-operator control, but it can pay an avoidable
round tax when several proof-frontier children fit inside the *same* frozen
row and draw caps.  This additive successor consumes the exact V1 frontier
and deterministically packs a ranked union of complete child catalogues.

The operator is deliberately pretarget.  It has no observer, kernel, hidden
law, random tape, signer, callback, model mutation, planner, or certificate
surface.  Source midranks retain their V1 role: they may change candidate
ordering, never statistical values or the learned quotient.  A separate
executor must bind every issued intent to append-only signed observations and
replay the resulting accounting.

The V1 single-candidate authorizer is not modified and remains the mandatory
``NO_BATCH_OPERATOR`` control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_adaptive_acquisition_round_bundle_authority_v1 as v1
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as public_graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.41.0"
PROFILE_KEY = "v075_cap_aware_batched_causal_acquisition_operator_v1"
PRODUCTION_INTEGRATION_READY = False

SELECTION_RULE = "RANKED_GREEDY_MINIMAL_CAUSAL_CONE_UNION_UNDER_FROZEN_CAPS"
NO_OPERATOR_CONTROL_PROFILE = v1.PROFILE_KEY

_ISSUER = object()

DOMAIN_TAGS = {
    "profile": "acfqp:v075-batched-causal-acquisition-profile:v1",
    "intent": "acfqp:v075-batched-causal-acquisition-intent:v1",
    "authorization": "acfqp:v075-batched-causal-acquisition-authorization:v1",
    "execution": "acfqp:v075-batched-causal-acquisition-execution:v1",
}
if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("batched causal acquisition domains must be unique")


class V075BatchedCausalAcquisitionInvariantViolation(ValueError):
    """The frontier, ranked union, cap arithmetic, or append replay changed."""


def _fail(message: str) -> NoReturn:
    raise V075BatchedCausalAcquisitionInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchedCausalAcquisitionInvariantViolation(str(error)) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise V075BatchedCausalAcquisitionInvariantViolation(
            f"{label} must be one lowercase SHA-256 content ID"
        ) from error


class V075BatchedCausalAuthorizationOutcomeV1(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    NO_UNCERTAIN_PROOF_FRONTIER = "NO_UNCERTAIN_PROOF_FRONTIER"
    INCREMENTAL_CAP_EXHAUSTED = "INCREMENTAL_CAP_EXHAUSTED"


class V075BatchedCausalIntentKindV1(str, Enum):
    EXISTING_VALIDATION_PREFIX_EXTENSION = (
        "EXISTING_VALIDATION_PREFIX_EXTENSION"
    )
    NEW_CHILD_ROW_DISCOVERY = "NEW_CHILD_ROW_DISCOVERY"
    NEW_CHILD_ROW_VALIDATION = "NEW_CHILD_ROW_VALIDATION"


@dataclass(frozen=True, slots=True)
class V075BatchedCausalAcquisitionProfileV1:
    cap_profile_id: str
    maximum_new_child_action_rows: int
    maximum_incremental_draws: int
    child_row_initial_draws: int
    validation_promotion_draws: int
    selection_rule: str = SELECTION_RULE
    no_operator_control_profile: str = NO_OPERATOR_CONTROL_PROFILE

    def __post_init__(self) -> None:
        _cid(self.cap_profile_id, "operator cap profile")
        caps = worker.V075WorkerCapProfileV1()
        if (
            self.cap_profile_id != caps.cap_profile_id
            or self.maximum_new_child_action_rows
            != caps.maximum_new_child_action_rows
            or self.maximum_incremental_draws
            != caps.maximum_incremental_draws_per_adaptive_arm
            or self.child_row_initial_draws != v1.CHILD_ROW_INITIAL_DRAWS
            or self.validation_promotion_draws != v1.PROMOTION_DRAWS
            or self.selection_rule != SELECTION_RULE
            or self.no_operator_control_profile != NO_OPERATOR_CONTROL_PROFILE
        ):
            _fail("batched causal acquisition profile changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batched_causal_acquisition_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "cap_profile_id": self.cap_profile_id,
            "maximum_new_child_action_rows": self.maximum_new_child_action_rows,
            "maximum_incremental_draws": self.maximum_incremental_draws,
            "child_row_initial_draws": self.child_row_initial_draws,
            "validation_promotion_draws": self.validation_promotion_draws,
            "selection_rule": self.selection_rule,
            "no_operator_control_profile": self.no_operator_control_profile,
            "candidate_order_source": "FROZEN_V1_RANKED_CANDIDATE_IDS",
            "complete_child_catalogue_required": True,
            "duplicate_child_rows_charged_once": True,
            "duplicate_source_promotions_charged_once": True,
            "missing_child_optional_source_promotions_suppressed": True,
            "post_run_cap_adjustment_allowed": False,
            "prior_changes_statistical_model": False,
            "prior_changes_certificate": False,
        }

    @property
    def profile_id(self) -> str:
        return _hash("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "operator_profile_id": self.profile_id}


def freeze_v075_batched_causal_acquisition_profile_v1(
) -> V075BatchedCausalAcquisitionProfileV1:
    caps = worker.V075WorkerCapProfileV1()
    return V075BatchedCausalAcquisitionProfileV1(
        caps.cap_profile_id,
        caps.maximum_new_child_action_rows,
        caps.maximum_incremental_draws_per_adaptive_arm,
        v1.CHILD_ROW_INITIAL_DRAWS,
        v1.PROMOTION_DRAWS,
    )


@dataclass(frozen=True, slots=True)
class V075BatchedCausalAcquisitionIntentV1:
    _issuer: object = field(repr=False, compare=False)
    frontier_id: str
    operator_profile_id: str
    causal_candidate_ids: tuple[str, ...]
    occurrence_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    round_index: int
    kind: V075BatchedCausalIntentKindV1
    row_binding: public_graph.V075ObservationRowBindingV1
    observer_epoch_index: int
    accepted_draw_start: int
    accepted_draw_count: int
    accepted_draw_cap: int
    existing_stream_id: str | None
    dependency_intent_id: str | None

    def __post_init__(self) -> None:
        if self._issuer is not _ISSUER:
            _fail("batched causal intents are operator-issued only")
        for value, label in (
            (self.frontier_id, "intent frontier"),
            (self.operator_profile_id, "intent operator profile"),
            (self.occurrence_id, "intent occurrence"),
            (self.context_id, "intent context"),
        ):
            _cid(value, label)
        if self.existing_stream_id is not None:
            _cid(self.existing_stream_id, "intent existing stream")
        if self.dependency_intent_id is not None:
            _cid(self.dependency_intent_id, "intent dependency")
        if (
            type(self.causal_candidate_ids) is not tuple
            or not self.causal_candidate_ids
            or self.causal_candidate_ids
            != tuple(sorted(set(self.causal_candidate_ids)))
            or any(_cid(item, "intent causal candidate") != item for item in self.causal_candidate_ids)
            or self.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.round_index not in (1, 2)
            or type(self.kind) is not V075BatchedCausalIntentKindV1
            or type(self.row_binding)
            is not public_graph.V075ObservationRowBindingV1
            or self.row_binding.context_id != self.context_id
            or type(self.observer_epoch_index) is not int
            or type(self.accepted_draw_start) is not int
            or type(self.accepted_draw_count) is not int
            or type(self.accepted_draw_cap) is not int
            or self.accepted_draw_start <= 0
            or self.accepted_draw_count <= 0
            or self.accepted_draw_end > self.accepted_draw_cap
        ):
            _fail("batched causal intent is malformed")
        if self.kind is V075BatchedCausalIntentKindV1.EXISTING_VALIDATION_PREFIX_EXTENSION:
            if (
                self.existing_stream_id is None
                or self.dependency_intent_id is not None
                or self.observer_epoch_index <= 0
                or self.accepted_draw_start <= 1
                or self.accepted_draw_count != v1.PROMOTION_DRAWS
            ):
                _fail("batched source-prefix extension is invalid")
        elif self.kind is V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_DISCOVERY:
            if (
                self.existing_stream_id is not None
                or self.dependency_intent_id is not None
                or self.observer_epoch_index != 0
                or self.accepted_draw_start != 1
                or self.accepted_draw_count != v1.CHILD_DISCOVERY_DRAWS
                or self.accepted_draw_cap != v1.CHILD_DISCOVERY_DRAWS
            ):
                _fail("batched child discovery intent is invalid")
        elif (
            self.existing_stream_id is not None
            or self.dependency_intent_id is None
            or self.observer_epoch_index != 1
            or self.accepted_draw_start != 1
            or self.accepted_draw_count != v1.CHILD_VALIDATION_DRAWS
            or self.accepted_draw_cap != v1.CHILD_VALIDATION_ACCEPTED_DRAW_CAP
        ):
            _fail("batched child validation intent is invalid")

    @property
    def accepted_draw_end(self) -> int:
        return self.accepted_draw_start + self.accepted_draw_count - 1

    @property
    def lane(self) -> public_graph.V075ObservationLaneV1:
        return (
            public_graph.V075ObservationLaneV1.DISCOVERY
            if self.kind is V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_DISCOVERY
            else public_graph.V075ObservationLaneV1.VALIDATION
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batched_causal_acquisition_intent.v1",
            "schema_version": SCHEMA_VERSION,
            "frontier_id": self.frontier_id,
            "operator_profile_id": self.operator_profile_id,
            "causal_candidate_ids": list(self.causal_candidate_ids),
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
                self.kind is V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_VALIDATION
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
class _UnionFactsV1:
    selected_candidate_ids: tuple[str, ...]
    selected_child_row_ids: tuple[str, ...]
    selected_promotion_row_ids: tuple[str, ...]
    incremental_draw_count: int


def _candidate_order(
    frontier: v1.V075AdaptiveRoundBundleFrontierV1,
) -> tuple[v1.V075AdaptiveRoundBundleCandidateV1, ...]:
    by_id = {item.candidate_id: item for item in frontier.candidates}
    try:
        return tuple(by_id[item] for item in frontier.ranked_candidate_ids)
    except KeyError as error:  # pragma: no cover - V1 constructor prevents this
        raise V075BatchedCausalAcquisitionInvariantViolation(
            "V1 ranked candidate registry is incomplete"
        ) from error


def _union_facts(
    *,
    frontier: v1.V075AdaptiveRoundBundleFrontierV1,
    profile: V075BatchedCausalAcquisitionProfileV1,
) -> _UnionFactsV1:
    selected: list[str] = []
    child_rows: set[str] = set()
    promotion_rows: set[str] = set()
    base_child_rows = set(frontier.accounting.new_child_action_row_ids)
    for candidate in _candidate_order(frontier):
        if not candidate.cap_eligible:
            continue
        proposed_children = child_rows | set(candidate.new_child_action_row_ids)
        proposed_promotions = set(promotion_rows)
        # A missing-child proof failure is repaired by materializing the
        # complete missing child catalogue.  V1 additionally promoted the
        # already-observed parent prefix when room remained.  That promotion
        # is not in the minimal causal cone, so the batched successor omits it.
        if (
            candidate.kind
            is v1.V075BundleCandidateKindV1.SELECTED_ROW_VALIDATION_PROMOTION
            and candidate.root_promotion_included
        ):
            proposed_promotions.add(candidate.source_row_binding.row_binding_id)
        proposed_cost = (
            len(proposed_children) * profile.child_row_initial_draws
            + len(proposed_promotions) * profile.validation_promotion_draws
        )
        if (
            len(base_child_rows | proposed_children)
            <= profile.maximum_new_child_action_rows
            and frontier.accounting.incremental_draws_used + proposed_cost
            <= profile.maximum_incremental_draws
        ):
            selected.append(candidate.candidate_id)
            child_rows = proposed_children
            promotion_rows = proposed_promotions
    cost = (
        len(child_rows) * profile.child_row_initial_draws
        + len(promotion_rows) * profile.validation_promotion_draws
    )
    return _UnionFactsV1(
        tuple(selected),
        tuple(sorted(child_rows)),
        tuple(sorted(promotion_rows)),
        cost,
    )


def _context(context_id: str) -> public_authority.V075PublicReplicateContextV1:
    values = tuple(
        item
        for item in public_authority.freeze_v075_public_family_generation_v1().replicate_contexts
        if item.context_id == context_id
    )
    if len(values) != 1:
        _fail("operator frontier context is not preregistered")
    return values[0]


def _intent_sources(
    candidates: tuple[v1.V075AdaptiveRoundBundleCandidateV1, ...],
    row_id: str,
    *,
    child: bool,
) -> tuple[str, ...]:
    values = tuple(
        sorted(
            item.candidate_id
            for item in candidates
            if (
                row_id in item.new_child_action_row_ids
                if child
                else (
                    item.root_promotion_included
                    and item.source_row_binding.row_binding_id == row_id
                )
            )
        )
    )
    if not values:
        _fail("operator intent has no selected causal candidate")
    return values


@dataclass(frozen=True, slots=True)
class V075BatchedCausalAcquisitionAuthorizationV1:
    _issuer: object = field(repr=False, compare=False)
    frontier: v1.V075AdaptiveRoundBundleFrontierV1
    profile: V075BatchedCausalAcquisitionProfileV1
    outcome: V075BatchedCausalAuthorizationOutcomeV1
    selected_candidate_ids: tuple[str, ...]
    selected_child_row_ids: tuple[str, ...]
    selected_promotion_row_ids: tuple[str, ...]
    intents: tuple[V075BatchedCausalAcquisitionIntentV1, ...]
    incremental_draw_count: int
    authorization_sequence: int
    minimum_observer_sequence: int

    def __post_init__(self) -> None:
        if (
            self._issuer is not _ISSUER
            or type(self.frontier) is not v1.V075AdaptiveRoundBundleFrontierV1
            or type(self.profile) is not V075BatchedCausalAcquisitionProfileV1
            or type(self.outcome) is not V075BatchedCausalAuthorizationOutcomeV1
            or type(self.intents) is not tuple
            or self.authorization_sequence != 2 * self.frontier.round_index - 1
            or self.minimum_observer_sequence != self.authorization_sequence + 1
        ):
            _fail("batched causal authorization is malformed")
        expected = _union_facts(frontier=self.frontier, profile=self.profile)
        if (
            self.selected_candidate_ids != expected.selected_candidate_ids
            or self.selected_child_row_ids != expected.selected_child_row_ids
            or self.selected_promotion_row_ids != expected.selected_promotion_row_ids
            or self.incremental_draw_count != expected.incremental_draw_count
        ):
            _fail("batched causal authorization differs from exact union replay")
        authorized = self.outcome is V075BatchedCausalAuthorizationOutcomeV1.AUTHORIZED
        if authorized != bool(self.selected_candidate_ids):
            _fail("batched causal authorization status disagrees with selection")
        if not authorized:
            expected_status = (
                V075BatchedCausalAuthorizationOutcomeV1.NO_UNCERTAIN_PROOF_FRONTIER
                if not self.frontier.candidates
                else V075BatchedCausalAuthorizationOutcomeV1.INCREMENTAL_CAP_EXHAUSTED
            )
            if (
                self.outcome is not expected_status
                or self.selected_child_row_ids
                or self.selected_promotion_row_ids
                or self.intents
                or self.incremental_draw_count != 0
            ):
                _fail("nonauthorized batched causal result contains work")
            return
        selected = tuple(
            item
            for item in self.frontier.candidates
            if item.candidate_id in set(self.selected_candidate_ids)
        )
        if len(selected) != len(self.selected_candidate_ids):
            _fail("selected candidate registry is incomplete")
        discoveries = tuple(
            item
            for item in self.intents
            if item.kind is V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_DISCOVERY
        )
        extensions = tuple(
            item
            for item in self.intents
            if item.kind
            is V075BatchedCausalIntentKindV1.EXISTING_VALIDATION_PREFIX_EXTENSION
        )
        validations = tuple(
            item
            for item in self.intents
            if item.kind is V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_VALIDATION
        )
        if self.intents != (*discoveries, *extensions, *validations):
            _fail("batched intents violate the support phase barrier")
        if (
            tuple(item.row_binding.row_binding_id for item in discoveries)
            != self.selected_child_row_ids
            or tuple(item.row_binding.row_binding_id for item in validations)
            != self.selected_child_row_ids
            or tuple(item.row_binding.row_binding_id for item in extensions)
            != self.selected_promotion_row_ids
            or tuple(item.dependency_intent_id for item in validations)
            != tuple(item.intent_id for item in discoveries)
            or sum(item.accepted_draw_count for item in self.intents)
            != self.incremental_draw_count
            or any(
                item.frontier_id != self.frontier.frontier_id
                or item.operator_profile_id != self.profile.profile_id
                or item.occurrence_id != self.frontier.occurrence_id
                or item.context_id != self.frontier.context_id
                or item.arm is not self.frontier.arm
                or item.round_index != self.frontier.round_index
                or not set(item.causal_candidate_ids)
                <= set(self.selected_candidate_ids)
                for item in self.intents
            )
        ):
            _fail("batched intent registry differs from selected union")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batched_causal_acquisition_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "frontier_id": self.frontier.frontier_id,
            "operator_profile_id": self.profile.profile_id,
            "authorization_outcome": self.outcome.value,
            "selected_candidate_ids": list(self.selected_candidate_ids),
            "selected_child_row_ids": list(self.selected_child_row_ids),
            "selected_promotion_row_ids": list(self.selected_promotion_row_ids),
            "intent_ids": [item.intent_id for item in self.intents],
            "incremental_draw_count": self.incremental_draw_count,
            "authorization_sequence": self.authorization_sequence,
            "minimum_observer_sequence": self.minimum_observer_sequence,
            "observer_execution_phase_order": [
                "NEW_CHILD_DISCOVERY",
                "SUPPORT_FREEZE_REGISTER_BARRIER",
                "EXISTING_VALIDATION_PREFIX_EXTENSION",
                "NEW_CHILD_VALIDATION",
            ],
            "v1_single_candidate_control_retained": True,
            "frozen_before_target_access": True,
            "observer_calls": 0,
            "kernel_calls": 0,
            "world_model_rows_written": 0,
            "scientific_certificate_issued": False,
        }

    @property
    def authorization_id(self) -> str:
        return _hash("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "frontier": self.frontier.to_document(),
            "operator_profile": self.profile.to_document(),
            "intents": [item.to_document() for item in self.intents],
            "authorization_id": self.authorization_id,
        }


def authorize_v075_batched_causal_acquisition_v1(
    frontier: v1.V075AdaptiveRoundBundleFrontierV1,
) -> V075BatchedCausalAcquisitionAuthorizationV1:
    """Pack the ranked frozen frontier without any target access."""

    if type(frontier) is not v1.V075AdaptiveRoundBundleFrontierV1:
        _fail("batched causal operator requires one exact V1 frontier")
    profile = freeze_v075_batched_causal_acquisition_profile_v1()
    facts = _union_facts(frontier=frontier, profile=profile)
    sequence = 2 * frontier.round_index - 1
    if not facts.selected_candidate_ids:
        status = (
            V075BatchedCausalAuthorizationOutcomeV1.NO_UNCERTAIN_PROOF_FRONTIER
            if not frontier.candidates
            else V075BatchedCausalAuthorizationOutcomeV1.INCREMENTAL_CAP_EXHAUSTED
        )
        return V075BatchedCausalAcquisitionAuthorizationV1(
            _ISSUER,
            frontier,
            profile,
            status,
            (),
            (),
            (),
            (),
            0,
            sequence,
            sequence + 1,
        )

    selected = tuple(
        item
        for item in frontier.candidates
        if item.candidate_id in set(facts.selected_candidate_ids)
    )
    context = _context(frontier.context_id)
    child_bindings: dict[str, public_graph.V075ObservationRowBindingV1] = {}
    for candidate in selected:
        if candidate.kind is not v1.V075BundleCandidateKindV1.MISSING_CHILD_COMPLETE_CATALOGUE:
            continue
        if candidate.child_catalogue is None or candidate.child_catalogue.context != context:
            _fail("selected child catalogue was transplanted")
        for action in candidate.child_catalogue.actions:
            binding = public_graph.observation_row_binding_v1(
                context, candidate.child_catalogue, action
            )
            prior = child_bindings.setdefault(binding.row_binding_id, binding)
            if prior != binding:
                _fail("one child row ID resolves to multiple bindings")
    if tuple(sorted(child_bindings)) != facts.selected_child_row_ids:
        _fail("selected union does not equal complete child catalogues")

    discoveries: list[V075BatchedCausalAcquisitionIntentV1] = []
    for row_id in facts.selected_child_row_ids:
        discoveries.append(
            V075BatchedCausalAcquisitionIntentV1(
                _ISSUER,
                frontier.frontier_id,
                profile.profile_id,
                _intent_sources(selected, row_id, child=True),
                frontier.occurrence_id,
                frontier.context_id,
                frontier.arm,
                frontier.round_index,
                V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_DISCOVERY,
                child_bindings[row_id],
                0,
                1,
                v1.CHILD_DISCOVERY_DRAWS,
                v1.CHILD_DISCOVERY_DRAWS,
                None,
                None,
            )
        )

    candidate_by_source = {
        item.source_row_binding.row_binding_id: item
        for item in sorted(selected, key=lambda item: item.candidate_id)
        if item.root_promotion_included
    }
    extensions: list[V075BatchedCausalAcquisitionIntentV1] = []
    for row_id in facts.selected_promotion_row_ids:
        candidate = candidate_by_source[row_id]
        extensions.append(
            V075BatchedCausalAcquisitionIntentV1(
                _ISSUER,
                frontier.frontier_id,
                profile.profile_id,
                _intent_sources(selected, row_id, child=False),
                frontier.occurrence_id,
                frontier.context_id,
                frontier.arm,
                frontier.round_index,
                V075BatchedCausalIntentKindV1.EXISTING_VALIDATION_PREFIX_EXTENSION,
                candidate.source_row_binding,
                candidate.source_observer_epoch_index,
                candidate.source_current_validation_draws + 1,
                v1.PROMOTION_DRAWS,
                candidate.source_validation_draw_cap,
                candidate.source_stream_id,
                None,
            )
        )

    validations = tuple(
        V075BatchedCausalAcquisitionIntentV1(
            _ISSUER,
            frontier.frontier_id,
            profile.profile_id,
            discovery.causal_candidate_ids,
            frontier.occurrence_id,
            frontier.context_id,
            frontier.arm,
            frontier.round_index,
            V075BatchedCausalIntentKindV1.NEW_CHILD_ROW_VALIDATION,
            discovery.row_binding,
            1,
            1,
            v1.CHILD_VALIDATION_DRAWS,
            v1.CHILD_VALIDATION_ACCEPTED_DRAW_CAP,
            None,
            discovery.intent_id,
        )
        for discovery in discoveries
    )
    return V075BatchedCausalAcquisitionAuthorizationV1(
        _ISSUER,
        frontier,
        profile,
        V075BatchedCausalAuthorizationOutcomeV1.AUTHORIZED,
        facts.selected_candidate_ids,
        facts.selected_child_row_ids,
        facts.selected_promotion_row_ids,
        (*discoveries, *extensions, *validations),
        facts.incremental_draw_count,
        sequence,
        sequence + 1,
    )


@dataclass(frozen=True, slots=True)
class V075BatchedCausalAcquisitionExecutionV1:
    authorization_id: str
    prior_batch_result_id: str
    resulting_batch_result_id: str
    executed_intent_ids: tuple[str, ...]
    appended_batch_ids: tuple[str, ...]
    prior_incremental_draws: int
    resulting_incremental_draws: int
    prior_child_row_count: int
    resulting_child_row_count: int

    def __post_init__(self) -> None:
        for value, label in (
            (self.authorization_id, "execution authorization"),
            (self.prior_batch_result_id, "execution prior result"),
            (self.resulting_batch_result_id, "execution resulting result"),
        ):
            _cid(value, label)
        if (
            type(self.executed_intent_ids) is not tuple
            or not self.executed_intent_ids
            or len(set(self.executed_intent_ids)) != len(self.executed_intent_ids)
            or type(self.appended_batch_ids) is not tuple
            or self.appended_batch_ids != tuple(sorted(set(self.appended_batch_ids)))
            or not self.appended_batch_ids
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.prior_incremental_draws,
                    self.resulting_incremental_draws,
                    self.prior_child_row_count,
                    self.resulting_child_row_count,
                )
            )
            or self.resulting_incremental_draws < self.prior_incremental_draws
            or self.resulting_child_row_count < self.prior_child_row_count
        ):
            _fail("batched causal execution evidence is malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_batched_causal_acquisition_execution.v1",
            "schema_version": SCHEMA_VERSION,
            "authorization_id": self.authorization_id,
            "prior_batch_result_id": self.prior_batch_result_id,
            "resulting_batch_result_id": self.resulting_batch_result_id,
            "executed_intent_ids": list(self.executed_intent_ids),
            "appended_batch_ids": list(self.appended_batch_ids),
            "prior_incremental_draws": self.prior_incremental_draws,
            "resulting_incremental_draws": self.resulting_incremental_draws,
            "prior_child_row_count": self.prior_child_row_count,
            "resulting_child_row_count": self.resulting_child_row_count,
            "exact_append_only_execution": True,
            "post_run_reorder_allowed": False,
        }

    @property
    def execution_id(self) -> str:
        return _hash("execution", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "execution_id": self.execution_id}


def _matching_batches(
    *,
    intent: V075BatchedCausalAcquisitionIntentV1,
    appended: tuple[Any, ...],
) -> tuple[Any, ...]:
    values = tuple(
        sorted(
            (
                item
                for item in appended
                if item.request.stream_identity.row_binding_id
                == intent.row_binding.row_binding_id
                and item.request.stream_identity.lane is intent.lane
                and item.request.stream_identity.observer_epoch_index
                == intent.observer_epoch_index
                and (
                    intent.existing_stream_id is None
                    or item.request.stream_identity.stream_id == intent.existing_stream_id
                )
            ),
            key=lambda item: item.request.accepted_draw_start,
        )
    )
    if (
        not values
        or values[0].request.accepted_draw_start != intent.accepted_draw_start
        or values[-1].request.accepted_draw_end != intent.accepted_draw_end
        or any(
            left.request.accepted_draw_end + 1 != right.request.accepted_draw_start
            for left, right in zip(values, values[1:])
        )
        or sum(item.request.accepted_draw_count for item in values)
        != intent.accepted_draw_count
        or any(item.request.accepted_draw_cap != intent.accepted_draw_cap for item in values)
    ):
        _fail("appended batches differ from one frozen batched intent")
    return values


def verify_v075_batched_causal_acquisition_execution_v1(
    *,
    authorization: V075BatchedCausalAcquisitionAuthorizationV1,
    resulting_batch_result: Any,
) -> V075BatchedCausalAcquisitionExecutionV1:
    """Replay exactly one executed multi-candidate union."""

    from acfqp import v075_batch_native_statistical_backend_v1 as backend

    if (
        type(authorization) is not V075BatchedCausalAcquisitionAuthorizationV1
        or authorization.outcome is not V075BatchedCausalAuthorizationOutcomeV1.AUTHORIZED
        or type(resulting_batch_result) is not backend.V075BatchNativeBackendResultV1
    ):
        _fail("execution verifier requires one authorized batched result")
    frontier = authorization.frontier
    if (
        resulting_batch_result.request.occurrence_id != frontier.occurrence_id
        or resulting_batch_result.request.context.context_id != frontier.context_id
        or resulting_batch_result.request.arm is not frontier.arm
    ):
        _fail("batched execution crossed occurrence, context, or arm")
    before = set(frontier.preproposal_batch_ids)
    after = {item.batch_id for item in resulting_batch_result.request.batches}
    if not before < after:
        _fail("batched execution did not append to the frozen batch set")
    appended = tuple(
        item
        for item in resulting_batch_result.request.batches
        if item.batch_id not in before
    )
    consumed: set[str] = set()
    for intent in authorization.intents:
        matches = _matching_batches(intent=intent, appended=appended)
        ids = {item.batch_id for item in matches}
        if consumed & ids:
            _fail("one appended batch was charged to multiple batched intents")
        consumed.update(ids)
    if consumed != {item.batch_id for item in appended}:
        _fail("batched execution appended an unauthorized observation")
    resulting = v1.replay_v075_incremental_accounting_v1(resulting_batch_result)
    prior = frontier.accounting
    if (
        resulting.incremental_draws_used
        != prior.incremental_draws_used + authorization.incremental_draw_count
        or len(resulting.new_child_action_row_ids)
        != len(prior.new_child_action_row_ids)
        + len(authorization.selected_child_row_ids)
    ):
        _fail("resulting accounting differs from the authorized exact union")
    return V075BatchedCausalAcquisitionExecutionV1(
        authorization.authorization_id,
        frontier.batch_result_id,
        resulting_batch_result.result_id,
        tuple(item.intent_id for item in authorization.intents),
        tuple(sorted(consumed)),
        prior.incremental_draws_used,
        resulting.incremental_draws_used,
        len(prior.new_child_action_row_ids),
        len(resulting.new_child_action_row_ids),
    )


__all__ = [
    "NO_OPERATOR_CONTROL_PROFILE",
    "PROFILE_KEY",
    "PRODUCTION_INTEGRATION_READY",
    "SELECTION_RULE",
    "V075BatchedCausalAcquisitionAuthorizationV1",
    "V075BatchedCausalAcquisitionExecutionV1",
    "V075BatchedCausalAcquisitionIntentV1",
    "V075BatchedCausalAcquisitionInvariantViolation",
    "V075BatchedCausalAcquisitionProfileV1",
    "V075BatchedCausalAuthorizationOutcomeV1",
    "V075BatchedCausalIntentKindV1",
    "authorize_v075_batched_causal_acquisition_v1",
    "freeze_v075_batched_causal_acquisition_profile_v1",
    "verify_v075_batched_causal_acquisition_execution_v1",
]
