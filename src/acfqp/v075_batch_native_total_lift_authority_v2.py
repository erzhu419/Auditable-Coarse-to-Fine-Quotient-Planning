"""Exact-V2 batch backend and total-lift construction authority.

This leaf consumes the aggregate-only V2 observer lineage.  It never expands
one batch into per-draw records and it never manufactures a historical V1
observer or target-namespace claim.  A statistical candidate is built from a
discovery-frozen support and the latest validation epoch for each ground row.
The independent total lift then evaluates the selected deterministic policy on
the complete exact H=2 kernel.  Exact outcomes outside the selected row's
frozen support enter one absorbing policy-abort failure with zero continuation
reward.

The public construction entry point is a non-scientific, noncertificate
control.  This module contains no production compiler or total-lift issuer.
Production remains structurally locked until a complete five-arm acquisition
terminal and V2 occurrence lifecycle are independently replayed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Iterable, Mapping

from acfqp.h2_graph_transition_engine_v1 import (
    H2GraphActionV1,
    H2GraphKernelV1,
    H2GraphTransitionAtomV1,
)
from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_statistical_backend_v1 as identity_backend
from acfqp import v075_batched_observer_authority_v2 as batched_v2
from acfqp import v075_private_observer_boundary_v2 as observer_v2
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker


SCHEMA_VERSION = "2.0.0"
PROPOSED_CONTRACT_VERSION = "1.45.0"
PROFILE_KEY = "v075_batch_native_total_lift_authority_v2"

PER_DRAW_CAPABILITY_EXPANSION_ALLOWED = False
LEGACY_OBSERVER_AUTHORITY_PROJECTION_ALLOWED = False
LEGACY_TARGET_NAMESPACE_PROJECTION_ALLOWED = False
OFFICIAL_EXECUTION_ALLOWED = False
SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED = False
EXACT_TOTAL_LIFT_IS_POST_PLAN_INDEPENDENT_EVALUATION = True
EXACT_PRIVATE_ROWS_AVAILABLE_TO_BACKEND_POLICY = False
EXACT_TOTAL_LIFT_COUNTS_AS_OPERATIONAL_ABSTRACT_PLANNING = False
MAX_CLAIMED_ARTIFACT_BYTES = 64 * 1024 * 1024

DOMAIN_TAGS = {
    "modeled_outcome": "acfqp:v075-v2-modeled-outcome:v1",
    "statistical_row": "acfqp:v075-v2-statistical-row:v1",
    "policy_choice": "acfqp:v075-v2-policy-choice:v1",
    "backend": "acfqp:v075-v2-statistical-backend-result:v1",
    "exact_row": "acfqp:v075-v2-exact-row-binding:v1",
    "total_lift": "acfqp:v075-v2-total-lift-result:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("V0-075 V2 total-lift content domains overlap")


class V075BatchNativeTotalLiftV2InvariantViolation(ValueError):
    """A V2 aggregate, statistical model, policy, or exact lift was invalid."""


def _fail(message: str) -> None:
    raise V075BatchNativeTotalLiftV2InvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075BatchNativeTotalLiftV2InvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075BatchNativeTotalLiftV2InvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _canonical_claim_bytes(raw: bytes, label: str) -> None:
    if (
        type(raw) is not bytes
        or not raw
        or len(raw) > MAX_CLAIMED_ARTIFACT_BYTES
    ):
        _fail(f"{label} bytes are empty, mistyped, or over cap")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075BatchNativeTotalLiftV2InvariantViolation(
            f"{label} bytes are not strict canonical JSON"
        ) from error
    if canonical_json_bytes(document) != raw:
        _fail(f"{label} bytes are not canonical JSON")


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("V2 total-lift arithmetic must remain exact")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _action(value: Any, field_name: str) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
        or value[0] >= value[1]
        or value[2] not in value[:2]
    ):
        _fail(f"{field_name} is not one canonical ground action")
    return value


class V075V2BackendScope(str, Enum):
    CONSTRUCTION_ONLY = "CONSTRUCTION_ONLY"


@dataclass(frozen=True, slots=True)
class V075V2ModeledOutcome:
    next_state_id: str
    next_ranks: tuple[int, ...]
    failure: bool
    terminal: bool
    count: int
    _outcome_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.next_state_id, "V2 modeled successor")
        if (
            type(self.next_ranks) is not tuple
            or not self.next_ranks
            or any(type(item) is not int or item < 0 for item in self.next_ranks)
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or type(self.count) is not int
            or self.count <= 0
        ):
            _fail("V2 modeled outcome is malformed")
        object.__setattr__(
            self,
            "_outcome_id",
            _hash("modeled_outcome", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_v2_modeled_outcome.v1",
            "schema_version": SCHEMA_VERSION,
            "next_state_id": self.next_state_id,
            "next_ranks": list(self.next_ranks),
            "failure": self.failure,
            "terminal": self.terminal,
            "count": self.count,
        }

    @property
    def outcome_id(self) -> str:
        return self._outcome_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_id": self.outcome_id}


@dataclass(frozen=True, slots=True)
class V075V2StatisticalRow:
    row_binding: graph.V075ObservationRowBindingV1 = field(repr=False)
    discovery_batch_ids: tuple[str, ...]
    validation_batch_ids: tuple[str, ...]
    support_evidence_ids: tuple[str, ...]
    outcomes: tuple[V075V2ModeledOutcome, ...]
    other_count: int
    draw_count: int
    reward: Fraction
    _row_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.row_binding) is not graph.V075ObservationRowBindingV1
            or type(self.discovery_batch_ids) is not tuple
            or not self.discovery_batch_ids
            or self.discovery_batch_ids
            != tuple(sorted(set(self.discovery_batch_ids)))
            or type(self.validation_batch_ids) is not tuple
            or not self.validation_batch_ids
            or self.validation_batch_ids
            != tuple(sorted(set(self.validation_batch_ids)))
            or set(self.discovery_batch_ids) & set(self.validation_batch_ids)
            or type(self.support_evidence_ids) is not tuple
            or not self.support_evidence_ids
            or self.support_evidence_ids
            != tuple(sorted(set(self.support_evidence_ids)))
            or type(self.outcomes) is not tuple
            or not self.outcomes
            or any(type(item) is not V075V2ModeledOutcome for item in self.outcomes)
            or tuple(item.outcome_id for item in self.outcomes)
            != tuple(sorted({item.outcome_id for item in self.outcomes}))
            or type(self.other_count) is not int
            or self.other_count < 0
            or type(self.draw_count) is not int
            or self.draw_count <= 0
            or sum(item.count for item in self.outcomes) + self.other_count
            != self.draw_count
            or type(self.reward) is not Fraction
            or self.reward < 0
        ):
            _fail("V2 statistical row is incomplete or noncanonical")
        object.__setattr__(
            self,
            "_row_id",
            _hash("statistical_row", self._payload()),
        )

    @property
    def source_state_id(self) -> str:
        return self.row_binding.state_id

    @property
    def remaining_horizon(self) -> int:
        return self.row_binding.remaining_horizon

    @property
    def action(self) -> tuple[int, int, int]:
        return self.row_binding.action

    @property
    def modeled_keys(self) -> tuple[tuple[str, bool, bool], ...]:
        return tuple(
            sorted(
                (item.next_state_id, item.failure, item.terminal)
                for item in self.outcomes
            )
        )

    @property
    def empirical_failure_probability(self) -> Fraction:
        return Fraction(
            self.other_count
            + sum(item.count for item in self.outcomes if item.failure),
            self.draw_count,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_v2_statistical_row.v1",
            "schema_version": SCHEMA_VERSION,
            "row_binding_id": self.row_binding.row_binding_id,
            "source_state_id": self.source_state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "discovery_batch_ids": list(self.discovery_batch_ids),
            "validation_batch_ids": list(self.validation_batch_ids),
            "support_evidence_ids": list(self.support_evidence_ids),
            "outcome_ids": [item.outcome_id for item in self.outcomes],
            "other_count": self.other_count,
            "draw_count": self.draw_count,
            "reward": _fdoc(self.reward),
            "empirical_failure_probability": _fdoc(
                self.empirical_failure_probability
            ),
            "support_frozen_before_validation": True,
            "unmodeled_outcome_semantics": "POLICY_ABORT_FAILURE",
        }

    @property
    def row_id(self) -> str:
        return self._row_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_binding": self.row_binding.to_document(),
            "outcomes": [item.to_document() for item in self.outcomes],
            "row_id": self.row_id,
        }


@dataclass(frozen=True, slots=True)
class V075V2PolicyChoice:
    state_id: str
    remaining_horizon: int
    action: tuple[int, int, int]
    statistical_row_id: str
    _choice_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.state_id, "V2 policy state")
        _cid(self.statistical_row_id, "V2 policy row")
        _action(self.action, "V2 policy action")
        if type(self.remaining_horizon) is not int or self.remaining_horizon not in (
            1,
            2,
        ):
            _fail("V2 policy horizon is invalid")
        object.__setattr__(
            self,
            "_choice_id",
            _hash("policy_choice", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_v2_policy_choice.v1",
            "schema_version": SCHEMA_VERSION,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "statistical_row_id": self.statistical_row_id,
        }

    @property
    def choice_id(self) -> str:
        return self._choice_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "choice_id": self.choice_id}


_BACKEND_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075V2StatisticalBackendResult:
    _issuer: object = field(repr=False, compare=False)
    scope: V075V2BackendScope
    occurrence_identity: (
        identity_backend.V075BatchNativeOccurrenceIdentityV1
    )
    lineage_id: str
    rows: tuple[V075V2StatisticalRow, ...]
    policy: tuple[V075V2PolicyChoice, ...]
    structurally_complete: bool
    readiness_reason: str
    _backend_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            replayed_identity = (
                identity_backend.replay_v075_batch_native_occurrence_identity_v1(
                    self.occurrence_identity
                )
            )
        except identity_backend.V075BatchNativeBackendInvariantViolation as error:
            raise V075BatchNativeTotalLiftV2InvariantViolation(str(error)) from error
        _cid(self.lineage_id, "V2 backend lineage")
        if (
            self._issuer is not _BACKEND_ISSUER
            or type(self.scope) is not V075V2BackendScope
            or type(self.rows) is not tuple
            or not self.rows
            or any(type(item) is not V075V2StatisticalRow for item in self.rows)
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or type(self.policy) is not tuple
            or any(type(item) is not V075V2PolicyChoice for item in self.policy)
            or tuple(
                (item.remaining_horizon, item.state_id)
                for item in self.policy
            )
            != tuple(
                sorted(
                    {
                        (item.remaining_horizon, item.state_id)
                        for item in self.policy
                    },
                    key=lambda item: (-item[0], item[1]),
                )
            )
            or type(self.structurally_complete) is not bool
            or type(self.readiness_reason) is not str
            or not self.readiness_reason
            or self.structurally_complete != bool(self.policy)
            or replayed_identity.occurrence_id
            != self.occurrence_identity.occurrence_id
        ):
            _fail("V2 statistical backend result is caller-minted or invalid")
        row_by_id = {item.row_id: item for item in self.rows}
        if any(
            choice.statistical_row_id not in row_by_id
            or row_by_id[choice.statistical_row_id].source_state_id
            != choice.state_id
            or row_by_id[choice.statistical_row_id].remaining_horizon
            != choice.remaining_horizon
            or row_by_id[choice.statistical_row_id].action != choice.action
            for choice in self.policy
        ):
            _fail("V2 statistical policy is not bound to its rows")
        object.__setattr__(
            self,
            "_backend_id",
            _hash("backend", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_v2_statistical_backend_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "occurrence_id": self.occurrence_identity.occurrence_id,
            "occurrence_identity": self.occurrence_identity.to_document(),
            "lineage_id": self.lineage_id,
            "row_ids": [item.row_id for item in self.rows],
            "policy_choice_ids": [item.choice_id for item in self.policy],
            "structurally_complete": self.structurally_complete,
            "readiness_reason": self.readiness_reason,
            "aggregate_only": True,
            "per_draw_capability_count": 0,
            "policy_source": "AGGREGATE_V2_EVIDENCE_ONLY",
            "compiler_role": "POST_ACQUISITION_GENERIC",
            "arm_specific_acquisition_semantics_claimed": False,
            "five_arm_campaign_equivalence_claimed": False,
            "exact_private_environment_accessed": False,
            "exact_row_accessed": False,
            "post_plan_total_lift_feedback_allowed": False,
            "authority_version": "V2",
            "namespace_version": "V2",
            "legacy_projection_used": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def backend_id(self) -> str:
        return self._backend_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "rows": [item.to_document() for item in self.rows],
            "policy": [item.to_document() for item in self.policy],
            "backend_id": self.backend_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _state_from_outcome(
    row: graph.V075ObservationRowBindingV1,
    outcome: observer_v2.V075BatchOutcomeAggregateV2,
) -> graph.V075SymbolicGraphStateV1:
    try:
        return graph.V075SymbolicGraphStateV1(
            row.context,
            outcome.next_ranks,
            outcome.failure,
        )
    except graph.V075PublicGraphSemanticsInvariantViolation as error:
        raise V075BatchNativeTotalLiftV2InvariantViolation(str(error)) from error


def _bound_profiles(
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
) -> tuple[
    worker.V075WorkerThresholdProfileV1,
    worker.V075WorkerCapProfileV1,
]:
    try:
        namespace = lineage.closure.authority_binding.namespace
        thresholds = namespace.workload.threshold_profile
        caps = namespace.workload.cap_profile
    except AttributeError as error:
        raise V075BatchNativeTotalLiftV2InvariantViolation(
            "V2 lineage has no namespace-bound threshold/cap profiles"
        ) from error
    if (
        type(thresholds) is not worker.V075WorkerThresholdProfileV1
        or type(caps) is not worker.V075WorkerCapProfileV1
        or thresholds.threshold_profile_id
        != lineage.occurrence_identity.threshold_profile_id
        or caps.cap_profile_id != lineage.occurrence_identity.cap_profile_id
    ):
        _fail(
            "V2 lineage occurrence identity does not match its "
            "namespace-bound threshold/cap profiles"
        )
    return thresholds, caps


def _compile_statistical_rows(
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
) -> tuple[V075V2StatisticalRow, ...]:
    grouped: dict[
        str,
        list[observer_v2.V075SignedObservationBatchV2],
    ] = {}
    for batch in lineage.batches:
        grouped.setdefault(batch.request.stream_identity.row_binding_id, []).append(
            batch
        )
    rows: list[V075V2StatisticalRow] = []
    for row_binding_id in sorted(grouped):
        values = grouped[row_binding_id]
        discoveries = tuple(
            item
            for item in values
            if item.request.stream_identity.lane
            is graph.V075ObservationLaneV1.DISCOVERY
        )
        validation_epochs = sorted(
            {
                item.request.stream_identity.observer_epoch_index
                for item in values
                if item.request.stream_identity.lane
                is graph.V075ObservationLaneV1.VALIDATION
            }
        )
        if not discoveries or not validation_epochs:
            continue
        latest_epoch = validation_epochs[-1]
        validations = tuple(
            item
            for item in values
            if item.request.stream_identity.lane
            is graph.V075ObservationLaneV1.VALIDATION
            and item.request.stream_identity.observer_epoch_index == latest_epoch
        )
        row_binding = discoveries[0].request.stream_identity.row_binding
        if any(
            item.request.stream_identity.row_binding != row_binding
            for item in discoveries + validations
        ):
            _fail("one V2 statistical row mixes row bindings")
        discovery_support_keys = {
            (
                item.request.stream_identity.stream_id,
                item.request.stream_identity.support_epoch_id,
                item.request.stream_identity.support_chain_id,
                item.request.stream_identity.pairing_lineage_id,
                item.request.stream_identity.pairing_group_id,
                item.request.stream_identity.observer_epoch_index,
            )
            for item in discoveries
        }
        validation_support_keys = {
            (
                item.request.stream_identity.stream_id,
                item.request.stream_identity.support_epoch_id,
                item.request.stream_identity.support_chain_id,
                item.request.stream_identity.pairing_lineage_id,
                item.request.stream_identity.pairing_group_id,
                item.request.stream_identity.observer_epoch_index,
            )
            for item in validations
        }
        if (
            len(discovery_support_keys) != 1
            or len(validation_support_keys) != 1
        ):
            _fail(
                "one V2 statistical row/epoch mixes stream or support "
                "identities"
            )
        leaf = validations[0].request.stream_identity.pairing_authority.support_chain.leaf
        evidence = tuple(
            item
            for item in leaf.evidence
            if type(item) is graph.V075BatchAggregateSupportEvidenceV1
        )
        if not evidence or len(evidence) != len(leaf.evidence):
            continue
        discovery_by_id = {item.batch_id: item for item in discoveries}
        support_states: dict[
            tuple[str, bool, bool],
            graph.V075SymbolicGraphStateV1,
        ] = {}
        for item in evidence:
            source = discovery_by_id.get(item.discovery_batch_id)
            if (
                source is None
                or source.request.request_id != item.discovery_request_id
                or item.row_binding != row_binding
                or item.source_observer_epoch_index != 0
            ):
                _fail("V2 support evidence is not bound to discovery")
            source_outcomes = {
                outcome.outcome_id: outcome for outcome in source.outcomes
            }
            observed = source_outcomes.get(item.discovery_outcome_id)
            if (
                observed is None
                or observed.count != item.discovery_outcome_count
                or _state_from_outcome(row_binding, observed)
                != item.observed_state
            ):
                _fail("V2 discovery support evidence changed")
            support_states[
                (
                    item.observed_state.state_id,
                    item.observed_state.failure,
                    observed.terminal,
                )
            ] = item.observed_state
        counts: dict[tuple[str, bool, bool], int] = {}
        states: dict[tuple[str, bool, bool], graph.V075SymbolicGraphStateV1] = {}
        other = 0
        rewards: set[Fraction] = set()
        draw_count = 0
        for batch in validations:
            draw_count += batch.request.accepted_draw_count
            for outcome in batch.outcomes:
                rewards.add(outcome.realized_row_reward)
                state = _state_from_outcome(row_binding, outcome)
                key = (state.state_id, outcome.failure, outcome.terminal)
                if (
                    state.state_id,
                    state.failure,
                    outcome.terminal,
                ) in support_states:
                    counts[key] = counts.get(key, 0) + outcome.count
                    states[key] = state
                else:
                    other += outcome.count
        if (
            not counts
            or len(rewards) != 1
            or sum(counts.values()) + other != draw_count
        ):
            continue
        modeled = tuple(
            sorted(
                (
                    V075V2ModeledOutcome(
                        key[0],
                        states[key].ranks,
                        key[1],
                        key[2],
                        count,
                    )
                    for key, count in counts.items()
                ),
                key=lambda item: item.outcome_id,
            )
        )
        rows.append(
            V075V2StatisticalRow(
                row_binding,
                tuple(sorted(item.batch_id for item in discoveries)),
                tuple(sorted(item.batch_id for item in validations)),
                tuple(sorted(item.evidence_id for item in evidence)),
                modeled,
                other,
                draw_count,
                next(iter(rewards)),
            )
        )
    return tuple(sorted(rows, key=lambda item: item.row_id))


def _choose_row(
    candidates: tuple[tuple[V075V2StatisticalRow, Fraction, Fraction], ...],
    risk_tolerance: Fraction,
) -> V075V2StatisticalRow:
    feasible = tuple(item for item in candidates if item[1] <= risk_tolerance)
    pool = feasible if feasible else candidates
    if not pool:
        _fail("V2 policy selection has no row candidates")
    return max(
        pool,
        key=lambda item: (
            item[2] if feasible else -item[1],
            -item[1],
            tuple(-value for value in item[0].action),
        ),
    )[0]


def _compile_policy(
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    rows: tuple[V075V2StatisticalRow, ...],
    thresholds: worker.V075WorkerThresholdProfileV1,
) -> tuple[tuple[V075V2PolicyChoice, ...], str]:
    identity = lineage.occurrence_identity
    namespace = lineage.closure.authority_binding.namespace
    context = next(
        (
            item
            for item in namespace.family.replicate_contexts
            if item.context_id == identity.context_id
        ),
        None,
    )
    if context is None:
        _fail("V2 occurrence context is absent from its namespace")
    by_key = {
        (item.source_state_id, item.remaining_horizon, item.action): item
        for item in rows
    }
    root = graph.root_catalogue_v1(context)
    if any(
        (root.state.state_id, 2, action) not in by_key
        for action in root.actions
    ):
        return (), "ROOT_ACTION_ROWS_INCOMPLETE"
    modeled_children: dict[str, graph.V075SymbolicGraphStateV1] = {}
    for action in root.actions:
        row = by_key[(root.state.state_id, 2, action)]
        for outcome in row.outcomes:
            if outcome.failure:
                continue
            state = graph.V075SymbolicGraphStateV1(
                context,
                outcome.next_ranks,
                False,
            )
            modeled_children[state.state_id] = state
    child_choice: dict[str, V075V2StatisticalRow] = {}
    for state_id in sorted(modeled_children):
        state = modeled_children[state_id]
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            graph.legal_action_triples_v1(context, state.ranks, state.failure),
        )
        candidates = tuple(
            (
                by_key[(state_id, 1, action)],
                by_key[(state_id, 1, action)].empirical_failure_probability,
                by_key[(state_id, 1, action)].reward,
            )
            for action in catalogue.actions
            if (state_id, 1, action) in by_key
        )
        if len(candidates) != len(catalogue.actions):
            return (), "MODELED_CHILD_ACTION_ROWS_INCOMPLETE"
        child_choice[state_id] = _choose_row(
            candidates,
            thresholds.risk_tolerance,
        )
    root_candidates = []
    for action in root.actions:
        row = by_key[(root.state.state_id, 2, action)]
        risk = Fraction(row.other_count, row.draw_count)
        reward = row.reward
        for outcome in row.outcomes:
            probability = Fraction(outcome.count, row.draw_count)
            if outcome.failure:
                risk += probability
                continue
            child = child_choice.get(outcome.next_state_id)
            if child is None:
                risk += probability
                continue
            risk += probability * child.empirical_failure_probability
            reward += probability * child.reward
        root_candidates.append((row, risk, reward))
    root_choice = _choose_row(
        tuple(root_candidates),
        thresholds.risk_tolerance,
    )
    choices = [
        V075V2PolicyChoice(
            root.state.state_id,
            2,
            root_choice.action,
            root_choice.row_id,
        )
    ]
    choices.extend(
        V075V2PolicyChoice(
            state_id,
            1,
            child_choice[state_id].action,
            child_choice[state_id].row_id,
        )
        for state_id in sorted(child_choice)
    )
    return (
        tuple(
            sorted(
                choices,
                key=lambda item: (-item.remaining_horizon, item.state_id),
            )
        ),
        "READY_FOR_EXACT_TOTAL_LIFT",
    )


def _compile_backend(
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
) -> V075V2StatisticalBackendResult:
    if (
        type(lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or lineage.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail(
            "V2 generic backend currently accepts construction lifecycle "
            "controls only"
        )
    try:
        expected_issuer = (
            batched_v2._CONSTRUCTION_LINEAGE_ISSUER  # noqa: SLF001
        )
        if lineage._issuer is not expected_issuer:  # noqa: SLF001
            _fail("V2 aggregate lineage has no registered scope issuer")
        replayed_lineage = batched_v2.V075BatchOccurrenceLineageV2(
            expected_issuer,
            lineage.scope,
            identity_backend.replay_v075_batch_native_occurrence_identity_v1(
                lineage.occurrence_identity
            ),
            lineage.closure,
            lineage.closure_verification,
            lineage.public_verifications,
            lineage.sequence_verifications,
            lineage.private_reveal_attestation_bytes_sha256,
            lineage.authorization_bytes_sha256,
            lineage.namespace_bytes_sha256,
            lineage.closure_bytes_sha256,
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        batched_v2.V075BatchedObserverV2InvariantViolation,
        identity_backend.V075BatchNativeBackendInvariantViolation,
    ) as error:
        if type(error) is V075BatchNativeTotalLiftV2InvariantViolation:
            raise
        raise V075BatchNativeTotalLiftV2InvariantViolation(
            "V2 aggregate lineage full-graph reconstruction failed"
        ) from error
    if (
        replayed_lineage.lineage_id != lineage.lineage_id
        or replayed_lineage.canonical_bytes != lineage.canonical_bytes
    ):
        _fail("V2 aggregate lineage differs from full-graph reconstruction")
    lineage = replayed_lineage
    scope = V075V2BackendScope.CONSTRUCTION_ONLY
    thresholds, _caps = _bound_profiles(lineage)
    rows = _compile_statistical_rows(lineage)
    if not rows:
        _fail("V2 aggregate lineage produced no validated statistical rows")
    policy, reason = _compile_policy(
        lineage=lineage,
        rows=rows,
        thresholds=thresholds,
    )
    return V075V2StatisticalBackendResult(
        _BACKEND_ISSUER,
        scope,
        lineage.occurrence_identity,
        lineage.lineage_id,
        rows,
        policy,
        bool(policy),
        reason,
    )


def compile_v075_construction_statistical_backend_v2(
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
) -> V075V2StatisticalBackendResult:
    """Compile a construction-only aggregate lineage without promotion."""

    if (
        type(lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or lineage.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail("construction backend rejects production or duck lineage")
    return _compile_backend(lineage)


@dataclass(frozen=True, slots=True)
class _ExactRow:
    row_binding: graph.V075ObservationRowBindingV1
    atoms: tuple[H2GraphTransitionAtomV1, ...]
    _row_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.row_binding) is not graph.V075ObservationRowBindingV1
            or type(self.atoms) is not tuple
            or not self.atoms
            or any(type(item) is not H2GraphTransitionAtomV1 for item in self.atoms)
            or sum((item.probability for item in self.atoms), Fraction(0)) != 1
        ):
            _fail("V2 exact row is malformed")
        object.__setattr__(
            self,
            "_row_id",
            _hash(
                "exact_row",
                {
                    "schema": "acfqp.v075_v2_exact_row_binding.v1",
                    "schema_version": SCHEMA_VERSION,
                    "row_binding_id": self.row_binding.row_binding_id,
                    "atoms": [
                        {
                            "next_ranks": list(item.next_state.ranks),
                            "failure": item.failure,
                            "terminal": item.terminal,
                            "probability": _fdoc(item.probability),
                            "reward": _fdoc(item.realized_row_reward),
                            "spawn_cell": item.spawn_cell,
                            "spawn_rank": item.spawn_rank,
                        }
                        for item in self.atoms
                    ],
                },
            ),
        )

    @property
    def row_id(self) -> str:
        return self._row_id

    @property
    def reward(self) -> Fraction:
        return self.atoms[0].realized_row_reward


def _canonical_environment(
    value: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[tuple[tuple[int, Fraction], ...], ...]:
    try:
        environment = tuple(tuple(row) for row in value)
    except TypeError as error:
        raise V075BatchNativeTotalLiftV2InvariantViolation(
            "V2 private environment is not concrete"
        ) from error
    if (
        len(environment) != 3
        or any(
            not row
            or tuple(rank for rank, _ in row)
            != tuple(sorted({rank for rank, _ in row}))
            or any(
                type(rank) is not int
                or rank <= 0
                or type(probability) is not Fraction
                or probability <= 0
                for rank, probability in row
            )
            or sum((probability for _, probability in row), Fraction(0)) != 1
            for row in environment
        )
    ):
        _fail("V2 private environment is noncanonical")
    return environment


def _commitment_bound_environment(
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[
    tuple[tuple[tuple[int, Fraction], ...], ...],
    str,
    str,
]:
    environment = _canonical_environment(private_environment)
    try:
        commitment = (
            lineage.closure.authority_binding.namespace
            .environment_commitment
        )
        verification = public_authority.verify_opaque_environment_reveal_v1(
            commitment=commitment,
            secret_salt=private_salt,
            secret_laws=environment,
        )
    except (
        AttributeError,
        TypeError,
        ValueError,
        public_authority.V075PublicCampaignAuthorityInvariantViolation,
    ) as error:
        raise V075BatchNativeTotalLiftV2InvariantViolation(
            "V2 exact lift could not replay its committed private environment"
        ) from error
    if not verification.matched:
        _fail(
            "V2 exact lift private environment differs from the "
            "namespace commitment"
        )
    return (
        environment,
        commitment.commitment_id,
        verification.verification_id,
    )


def _exact_inventory(
    *,
    context: Any,
    law: tuple[tuple[int, Fraction], ...],
) -> dict[tuple[str, int, tuple[int, int, int]], _ExactRow]:
    kernel = H2GraphKernelV1(
        context.topology,
        context.rank_cap,
        context.horizon,
        law,
    )
    result: dict[tuple[str, int, tuple[int, int, int]], _ExactRow] = {}
    root = graph.root_catalogue_v1(context)
    children: dict[str, graph.V075SymbolicGraphStateV1] = {}

    def add(catalogue: graph.V075LegalActionCatalogueV1, action: tuple[int, int, int]) -> None:
        binding = graph.observation_row_binding_v1(context, catalogue, action)
        atoms = kernel.exact_atoms(
            catalogue.state.to_kernel_state(),
            H2GraphActionV1(*action),
            remaining_horizon=catalogue.remaining_horizon,
        )
        row = _ExactRow(binding, atoms)
        key = (binding.state_id, binding.remaining_horizon, binding.action)
        if key in result:
            _fail("V2 exact inventory repeats one row")
        result[key] = row
        if catalogue.remaining_horizon == 2:
            for atom in atoms:
                if atom.failure:
                    continue
                state = graph.V075SymbolicGraphStateV1(
                    context,
                    atom.next_state.ranks,
                    False,
                )
                prior = children.setdefault(state.state_id, state)
                if prior != state:
                    _fail("V2 exact successor identity collision")

    for action in root.actions:
        add(root, action)
    for state_id in sorted(children):
        state = children[state_id]
        catalogue = graph.V075LegalActionCatalogueV1(
            context,
            state,
            1,
            graph.legal_action_triples_v1(context, state.ranks, state.failure),
        )
        for action in catalogue.actions:
            add(catalogue, action)
    return result


@dataclass(frozen=True, slots=True)
class _GroundPoint:
    reward: Fraction
    failure: Fraction
    signature: tuple[tuple[str, int, tuple[int, int, int]], ...]


def _pareto(points: Iterable[_GroundPoint]) -> tuple[_GroundPoint, ...]:
    best_at_failure: dict[Fraction, _GroundPoint] = {}
    for item in points:
        prior = best_at_failure.get(item.failure)
        if (
            prior is None
            or item.reward > prior.reward
            or (
                item.reward == prior.reward
                and item.signature < prior.signature
            )
        ):
            best_at_failure[item.failure] = item
    kept = []
    best_reward: Fraction | None = None
    for failure in sorted(best_at_failure):
        point = best_at_failure[failure]
        if best_reward is not None and point.reward <= best_reward:
            continue
        kept.append(point)
        best_reward = point.reward
    return tuple(kept)


def _ground_optimum(
    *,
    context: Any,
    exact: Mapping[tuple[str, int, tuple[int, int, int]], _ExactRow],
    risk_tolerance: Fraction,
) -> _GroundPoint | None:
    root = graph.root_catalogue_v1(context)
    all_points: list[_GroundPoint] = []
    for root_action in root.actions:
        root_row = exact[(root.state.state_id, 2, root_action)]
        env_failure = sum(
            (item.probability for item in root_row.atoms if item.failure),
            Fraction(0),
        )
        child_weights: dict[str, Fraction] = {}
        child_states: dict[str, graph.V075SymbolicGraphStateV1] = {}
        for atom in root_row.atoms:
            if atom.failure:
                continue
            state = graph.V075SymbolicGraphStateV1(
                context,
                atom.next_state.ranks,
                False,
            )
            child_states[state.state_id] = state
            child_weights[state.state_id] = (
                child_weights.get(state.state_id, Fraction(0))
                + atom.probability
            )
        points = (
            _GroundPoint(
                root_row.reward,
                env_failure,
                ((root.state.state_id, 2, root_action),),
            ),
        )
        for state_id in sorted(child_states):
            state = child_states[state_id]
            actions = graph.legal_action_triples_v1(
                context,
                state.ranks,
                state.failure,
            )
            expanded = []
            for point in points:
                for action in actions:
                    child = exact[(state_id, 1, action)]
                    child_failure = sum(
                        (
                            item.probability
                            for item in child.atoms
                            if item.failure
                        ),
                        Fraction(0),
                    )
                    weight = child_weights[state_id]
                    expanded.append(
                        _GroundPoint(
                            point.reward + weight * child.reward,
                            point.failure + weight * child_failure,
                            point.signature + ((state_id, 1, action),),
                        )
                    )
            points = _pareto(expanded)
        all_points.extend(points)
    feasible = tuple(item for item in _pareto(all_points) if item.failure <= risk_tolerance)
    if not feasible:
        return None
    return max(feasible, key=lambda item: (item.reward, -item.failure, item.signature))


class V075V2TotalLiftStatus(str, Enum):
    EXACT_POSITIVE_CONSTRUCTION_CONTROL = "EXACT_POSITIVE_CONSTRUCTION_CONTROL"
    EXACT_GROUND_QUERY_INFEASIBLE = "EXACT_GROUND_QUERY_INFEASIBLE"
    EXACT_POLICY_RISK_FAILURE = "EXACT_POLICY_RISK_FAILURE"
    EXACT_POLICY_REGRET_FAILURE = "EXACT_POLICY_REGRET_FAILURE"
    STATISTICAL_BACKEND_INCOMPLETE = "STATISTICAL_BACKEND_INCOMPLETE"


_TOTAL_LIFT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075V2TotalLiftResult:
    _issuer: object = field(repr=False, compare=False)
    scope: V075V2BackendScope
    backend_id: str
    lineage_id: str
    occurrence_id: str
    exact_inventory_id: str
    environment_commitment_id: str
    environment_reveal_verification_id: str
    status: V075V2TotalLiftStatus
    selected_expected_reward: Fraction
    environment_failure_probability: Fraction
    policy_abort_failure_probability: Fraction
    selected_failure_probability: Fraction
    optimal_expected_reward: Fraction | None
    optimal_failure_probability: Fraction | None
    exact_normalized_regret: Fraction | None
    selected_policy_signature: tuple[
        tuple[str, int, tuple[int, int, int]],
        ...,
    ]
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.backend_id, "V2 total-lift backend"),
            (self.lineage_id, "V2 total-lift lineage"),
            (self.occurrence_id, "V2 total-lift occurrence"),
            (self.exact_inventory_id, "V2 exact inventory"),
            (
                self.environment_commitment_id,
                "V2 total-lift environment commitment",
            ),
            (
                self.environment_reveal_verification_id,
                "V2 total-lift environment reveal verification",
            ),
        ):
            _cid(value, label)
        if (
            self._issuer is not _TOTAL_LIFT_ISSUER
            or type(self.scope) is not V075V2BackendScope
            or type(self.status) is not V075V2TotalLiftStatus
            or any(
                type(item) is not Fraction
                for item in (
                    self.selected_expected_reward,
                    self.environment_failure_probability,
                    self.policy_abort_failure_probability,
                    self.selected_failure_probability,
                )
            )
            or self.selected_failure_probability
            != self.environment_failure_probability
            + self.policy_abort_failure_probability
            or not 0 <= self.selected_failure_probability <= 1
            or type(self.selected_policy_signature) is not tuple
            or self.scope is not V075V2BackendScope.CONSTRUCTION_ONLY
        ):
            _fail("V2 total-lift result is caller-minted or malformed")
        optional = (
            self.optimal_expected_reward,
            self.optimal_failure_probability,
            self.exact_normalized_regret,
        )
        if any(item is None for item in optional) != all(
            item is None for item in optional
        ):
            _fail("V2 optimal metrics are partially present")
        object.__setattr__(
            self,
            "_result_id",
            _hash("total_lift", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_v2_total_lift_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "scope": self.scope.value,
            "backend_id": self.backend_id,
            "lineage_id": self.lineage_id,
            "occurrence_id": self.occurrence_id,
            "exact_inventory_id": self.exact_inventory_id,
            "environment_commitment_id": self.environment_commitment_id,
            "environment_reveal_verification_id": (
                self.environment_reveal_verification_id
            ),
            "status": self.status.value,
            "selected_expected_reward": _fdoc(self.selected_expected_reward),
            "environment_failure_probability": _fdoc(
                self.environment_failure_probability
            ),
            "policy_abort_failure_probability": _fdoc(
                self.policy_abort_failure_probability
            ),
            "selected_failure_probability": _fdoc(
                self.selected_failure_probability
            ),
            "optimal_expected_reward": (
                None
                if self.optimal_expected_reward is None
                else _fdoc(self.optimal_expected_reward)
            ),
            "optimal_failure_probability": (
                None
                if self.optimal_failure_probability is None
                else _fdoc(self.optimal_failure_probability)
            ),
            "exact_normalized_regret": (
                None
                if self.exact_normalized_regret is None
                else _fdoc(self.exact_normalized_regret)
            ),
            "selected_policy_signature": [
                {
                    "state_id": state_id,
                    "remaining_horizon": horizon,
                    "action": list(action),
                }
                for state_id, horizon, action in self.selected_policy_signature
            ],
            "environment_failure_preserved": True,
            "unmodeled_outcome_semantics": "POLICY_ABORT_FAILURE",
            "policy_abort_continuation_reward": _fdoc(Fraction(0)),
            "full_exact_h2_inventory_reconstructed": True,
            "evaluation_order": (
                "FROZEN_AGGREGATE_POLICY_THEN_INDEPENDENT_EXACT_TOTAL_LIFT"
            ),
            "policy_selection_reopened": False,
            "exact_result_fed_back_to_backend": False,
            "counts_as_operational_abstract_planning": False,
            "execution_lane": "POST_PLAN_INDEPENDENT_EVALUATION",
            "per_draw_capability_expansion": False,
            "legacy_projection_used": False,
            "official_execution_allowed": False,
            "scientific_endpoint_credit_allowed": False,
        }

    @property
    def result_id(self) -> str:
        return self._result_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _evaluate_exact_lift(
    *,
    backend: V075V2StatisticalBackendResult,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075V2TotalLiftResult:
    if (
        type(backend) is not V075V2StatisticalBackendResult
        or backend._issuer is not _BACKEND_ISSUER
        or type(lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or backend.lineage_id != lineage.lineage_id
        or backend.occurrence_identity.occurrence_id
        != lineage.occurrence_identity.occurrence_id
        or backend.scope is not V075V2BackendScope.CONSTRUCTION_ONLY
        or lineage.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail("V2 exact lift inputs are stale, foreign, or untyped")
    expected_backend = _compile_backend(lineage)
    try:
        backend_bytes = backend.canonical_bytes
    except (AttributeError, TypeError, ValueError) as error:
        raise V075BatchNativeTotalLiftV2InvariantViolation(
            "V2 exact lift rejected a forged backend object"
        ) from error
    if (
        backend_bytes != expected_backend.canonical_bytes
        or backend.backend_id != expected_backend.backend_id
    ):
        _fail("V2 exact lift backend differs from evidence recomputation")
    return _evaluate_replayed_backend_exact_lift(
        backend=expected_backend,
        lineage=lineage,
        private_salt=private_salt,
        private_environment=private_environment,
    )


def _evaluate_replayed_backend_exact_lift(
    *,
    backend: V075V2StatisticalBackendResult,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075V2TotalLiftResult:
    """Evaluate a backend returned by this module's immediate replay.

    This helper is never an external trust boundary: public callers either
    enter through ``_evaluate_exact_lift`` (which recomputes a claimed
    backend), or through the combined construction builder below (which
    creates the backend locally before this call).
    """

    if (
        type(backend) is not V075V2StatisticalBackendResult
        or backend._issuer is not _BACKEND_ISSUER
        or type(lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or backend.scope is not V075V2BackendScope.CONSTRUCTION_ONLY
        or lineage.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
        or backend.lineage_id != lineage.lineage_id
        or backend.occurrence_identity.occurrence_id
        != lineage.occurrence_identity.occurrence_id
    ):
        _fail("replayed V2 backend/lift binding is invalid")
    (
        environment,
        environment_commitment_id,
        environment_reveal_verification_id,
    ) = _commitment_bound_environment(
        lineage=lineage,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    namespace = lineage.closure.authority_binding.namespace
    context_index = next(
        (
            index
            for index, item in enumerate(namespace.family.replicate_contexts)
            if item.context_id == lineage.occurrence_identity.context_id
        ),
        None,
    )
    if context_index is None:
        _fail("V2 exact lift context is absent from namespace")
    context = namespace.family.replicate_contexts[context_index]
    exact = _exact_inventory(
        context=context,
        law=environment[context_index],
    )
    inventory_id = hashlib.sha256(
        b"acfqp:v075-v2-exact-inventory:v1"
        + b"\x00"
        + canonical_json_bytes(
            {
                "context_id": context.context_id,
                "row_ids": sorted(item.row_id for item in exact.values()),
            }
        )
    ).hexdigest()
    thresholds, _ = _bound_profiles(lineage)
    optimum = _ground_optimum(
        context=context,
        exact=exact,
        risk_tolerance=thresholds.risk_tolerance,
    )
    if not backend.structurally_complete:
        return V075V2TotalLiftResult(
            _TOTAL_LIFT_ISSUER,
            backend.scope,
            backend.backend_id,
            backend.lineage_id,
            backend.occurrence_identity.occurrence_id,
            inventory_id,
            environment_commitment_id,
            environment_reveal_verification_id,
            V075V2TotalLiftStatus.STATISTICAL_BACKEND_INCOMPLETE,
            Fraction(0),
            Fraction(0),
            Fraction(1),
            Fraction(1),
            None if optimum is None else optimum.reward,
            None if optimum is None else optimum.failure,
            None if optimum is None else optimum.reward / thresholds.reward_ceiling,
            (),
        )
    rows = {item.row_id: item for item in backend.rows}
    choices = {
        (item.state_id, item.remaining_horizon): item for item in backend.policy
    }
    root = graph.root_catalogue_v1(context)
    root_choice = choices.get((root.state.state_id, 2))
    if root_choice is None:
        _fail("V2 selected policy lacks root choice")
    root_model = rows[root_choice.statistical_row_id]
    root_exact = exact[
        (root.state.state_id, 2, root_choice.action)
    ]
    selected_reward = root_exact.reward
    environment_failure = Fraction(0)
    policy_abort = Fraction(0)
    for root_atom in root_exact.atoms:
        root_weight = root_atom.probability
        if root_atom.failure:
            environment_failure += root_weight
            continue
        root_state = graph.V075SymbolicGraphStateV1(
            context,
            root_atom.next_state.ranks,
            False,
        )
        root_key = (root_state.state_id, False, root_atom.terminal)
        if root_key not in root_model.modeled_keys:
            policy_abort += root_weight
            continue
        child_choice = choices.get((root_state.state_id, 1))
        if child_choice is None:
            policy_abort += root_weight
            continue
        child_model = rows[child_choice.statistical_row_id]
        child_exact = exact[
            (root_state.state_id, 1, child_choice.action)
        ]
        selected_reward += root_weight * child_exact.reward
        for child_atom in child_exact.atoms:
            weight = root_weight * child_atom.probability
            if child_atom.failure:
                environment_failure += weight
                continue
            child_state = graph.V075SymbolicGraphStateV1(
                context,
                child_atom.next_state.ranks,
                False,
            )
            child_key = (
                child_state.state_id,
                False,
                child_atom.terminal,
            )
            if child_key not in child_model.modeled_keys:
                policy_abort += weight
    selected_failure = environment_failure + policy_abort
    selected_signature = tuple(
        (item.state_id, item.remaining_horizon, item.action)
        for item in backend.policy
    )
    if optimum is None:
        status = V075V2TotalLiftStatus.EXACT_GROUND_QUERY_INFEASIBLE
        optimal_reward = None
        optimal_failure = None
        regret = None
    else:
        optimal_reward = optimum.reward
        optimal_failure = optimum.failure
        regret = (
            optimum.reward - selected_reward
        ) / thresholds.reward_ceiling
        if selected_failure > thresholds.risk_tolerance:
            status = V075V2TotalLiftStatus.EXACT_POLICY_RISK_FAILURE
        elif regret > thresholds.normalized_regret_tolerance:
            status = V075V2TotalLiftStatus.EXACT_POLICY_REGRET_FAILURE
        else:
            status = (
                V075V2TotalLiftStatus.EXACT_POSITIVE_CONSTRUCTION_CONTROL
            )
    return V075V2TotalLiftResult(
        _TOTAL_LIFT_ISSUER,
        backend.scope,
        backend.backend_id,
        backend.lineage_id,
        backend.occurrence_identity.occurrence_id,
        inventory_id,
        environment_commitment_id,
        environment_reveal_verification_id,
        status,
        selected_reward,
        environment_failure,
        policy_abort,
        selected_failure,
        optimal_reward,
        optimal_failure,
        regret,
        selected_signature,
    )


def evaluate_v075_construction_total_lift_v2(
    *,
    backend: V075V2StatisticalBackendResult,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> V075V2TotalLiftResult:
    """Exact construction control; cannot be promoted to production."""

    if (
        type(backend) is not V075V2StatisticalBackendResult
        or backend.scope is not V075V2BackendScope.CONSTRUCTION_ONLY
        or type(lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or lineage.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail("construction total lift rejects production or duck inputs")
    return _evaluate_exact_lift(
        backend=backend,
        lineage=lineage,
        private_salt=private_salt,
        private_environment=private_environment,
    )


def build_v075_construction_backend_and_total_lift_v2(
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
) -> tuple[V075V2StatisticalBackendResult, V075V2TotalLiftResult]:
    """Replay once, then build both construction-control artifacts.

    The combined entry preserves the same exact arithmetic and evidence
    reconstruction as the separate public entries while avoiding a second
    full cryptographic lineage replay for a backend created in this call.
    """

    if (
        type(lineage) is not batched_v2.V075BatchOccurrenceLineageV2
        or lineage.scope
        is not batched_v2.V075BatchOccurrenceAuthorityScopeV2.CONSTRUCTION_ONLY
    ):
        _fail("combined construction builder rejects production or duck inputs")
    backend = _compile_backend(lineage)
    result = _evaluate_replayed_backend_exact_lift(
        backend=backend,
        lineage=lineage,
        private_salt=private_salt,
        private_environment=private_environment,
    )
    return backend, result


def verify_v075_construction_total_lift_bytes_v2(
    *,
    lineage: batched_v2.V075BatchOccurrenceLineageV2,
    private_salt: bytes,
    private_environment: Iterable[Iterable[tuple[int, Fraction]]],
    claimed_backend_bytes: bytes,
    claimed_total_lift_bytes: bytes,
) -> tuple[V075V2StatisticalBackendResult, V075V2TotalLiftResult]:
    """Independently reconstruct both construction artifacts from evidence."""

    _canonical_claim_bytes(claimed_backend_bytes, "claimed V2 backend")
    _canonical_claim_bytes(
        claimed_total_lift_bytes,
        "claimed V2 total lift",
    )
    expected_backend, expected_lift = (
        build_v075_construction_backend_and_total_lift_v2(
            lineage=lineage,
            private_salt=private_salt,
            private_environment=private_environment,
        )
    )
    if (
        type(claimed_backend_bytes) is not bytes
        or claimed_backend_bytes != expected_backend.canonical_bytes
    ):
        _fail("claimed V2 backend bytes differ from exact recomputation")
    if (
        type(claimed_total_lift_bytes) is not bytes
        or claimed_total_lift_bytes != expected_lift.canonical_bytes
    ):
        _fail("claimed V2 total-lift bytes differ from exact recomputation")
    return expected_backend, expected_lift


__all__ = [
    "LEGACY_OBSERVER_AUTHORITY_PROJECTION_ALLOWED",
    "LEGACY_TARGET_NAMESPACE_PROJECTION_ALLOWED",
    "EXACT_PRIVATE_ROWS_AVAILABLE_TO_BACKEND_POLICY",
    "EXACT_TOTAL_LIFT_COUNTS_AS_OPERATIONAL_ABSTRACT_PLANNING",
    "EXACT_TOTAL_LIFT_IS_POST_PLAN_INDEPENDENT_EVALUATION",
    "OFFICIAL_EXECUTION_ALLOWED",
    "PER_DRAW_CAPABILITY_EXPANSION_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_ENDPOINT_CREDIT_ALLOWED",
    "V075BatchNativeTotalLiftV2InvariantViolation",
    "V075V2BackendScope",
    "V075V2ModeledOutcome",
    "V075V2PolicyChoice",
    "V075V2StatisticalBackendResult",
    "V075V2StatisticalRow",
    "V075V2TotalLiftResult",
    "V075V2TotalLiftStatus",
    "build_v075_construction_backend_and_total_lift_v2",
    "compile_v075_construction_statistical_backend_v2",
    "evaluate_v075_construction_total_lift_v2",
    "verify_v075_construction_total_lift_bytes_v2",
]
