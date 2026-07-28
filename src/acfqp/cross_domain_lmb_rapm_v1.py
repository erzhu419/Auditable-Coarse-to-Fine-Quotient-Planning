"""Cross-domain relational-program transfer into held-out LMB targets.

This module is the Layered Matching Buffer arm of the V0-066 construction
slice.  It consumes, but never constructs, the portable relational skeleton
selected from graph observations by :mod:`portable_relational_skeleton_v1`.
The graph-selected operator tree has one open binary-relation slot.  A
query-neutral LMB bridge log audits every registered LMB binding and selects
``same_type(selected_tile, buffer_token)`` without receiving a held-out
target, query, plan, value, or certificate.

The bound action coordinate is therefore the number of already-buffered
tokens having the selected tile's type.  It is not a handwritten
``completes_match`` feature.  Three held-out six-tile LMB structures then
instantiate the same skeleton.  Their dynamics remain target-local: a failed
model proof authorizes only the selected root support and, after that sample
reveals a continuation, only the selected continuation support.  Evidence is
a deterministically replayable counter-based sample trace under an exact fixed
uniform concretizer over distinct ground actions.  Statistical confidence is
explicitly conditional on the registered SHA-256 random-oracle and
iid-simulator assumption; deterministic replay is not presented as an entropy
attestation.  No operational path enumerates a complete target transition
closure.

The result is deliberately narrow.  The registered graph and LMB adapters
are a human ontology/alignment prior.  Only the relational operator skeleton,
not a transition row or a world-model epoch, crosses domains.  The campaign
does not claim automatic ontology alignment, sample saving, scalar economics,
or official execution.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
import functools
import hashlib
import math
from typing import Any, Mapping

from acfqp.domains.matching_buffer import (
    LMBAction,
    LMBKernel,
    LMBState,
    LMBStatus,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.30.0"
PROFILE_KEY = "cross_domain_relational_lmb_statistical_rapm_v0"
SUCCESS_STATUS = "CERTIFIED_REGISTERED_CROSS_DOMAIN_LMB_RELATIONAL_RAPM"

HORIZON = 2
RISK_TOLERANCE = Fraction(1, 20)
REGRET_TOLERANCE = Fraction(1, 20)
REWARD_NORMALIZER = Fraction(2)
SAMPLE_COUNT_PER_SUPPORT = 16_384
HOEFFDING_RADIUS = Fraction(1, 60)
PER_ATOM_TAIL_UPPER = Fraction(1, 4_000)
PREREGISTERED_ATOM_OBLIGATIONS = 64
FAMILY_TAIL_UPPER = (
    PREREGISTERED_ATOM_OBLIGATIONS * PER_ATOM_TAIL_UPPER
)
FAMILY_CONFIDENCE_LOWER = 1 - FAMILY_TAIL_UPPER
POSITIVE_SUPPORT_COUNT = 6
POSITIVE_DRAW_COUNT = POSITIVE_SUPPORT_COUNT * SAMPLE_COUNT_PER_SUPPORT


DOMAIN_TAGS = {
    "semantics": "acfqp:cross-domain-lmb-semantics:v1",
    "context": "acfqp:cross-domain-lmb-context:v1",
    "bridge_row": "acfqp:cross-domain-lmb-bridge-row:v1",
    "bridge_log": "acfqp:cross-domain-lmb-bridge-log:v1",
    "binding_candidate": "acfqp:cross-domain-lmb-binding-candidate:v1",
    "binding": "acfqp:cross-domain-lmb-slot-binding:v1",
    "support": "acfqp:cross-domain-lmb-support:v1",
    "model_row": "acfqp:cross-domain-lmb-model-row:v1",
    "model": "acfqp:cross-domain-lmb-partial-statistical-rapm:v1",
    "audit": "acfqp:cross-domain-lmb-audit:v1",
    "authorization": "acfqp:cross-domain-lmb-authorization:v1",
    "sample_atom": "acfqp:cross-domain-lmb-sample-atom:v1",
    "sample_count": "acfqp:cross-domain-lmb-sample-count:v1",
    "trace": "acfqp:cross-domain-lmb-counter-trace:v1",
    "evidence_verification": (
        "acfqp:cross-domain-lmb-evidence-verification:v1"
    ),
    "query": "acfqp:cross-domain-lmb-query:v1",
    "occurrence": "acfqp:cross-domain-lmb-occurrence:v1",
    "cold": "acfqp:cross-domain-lmb-cold-control:v1",
    "context_result": "acfqp:cross-domain-lmb-context-result:v1",
    "no_transfer": "acfqp:cross-domain-lmb-no-transfer:v1",
    "wrong_binding": "acfqp:cross-domain-lmb-wrong-binding:v1",
    "ood": "acfqp:cross-domain-lmb-ood:v1",
    "permutation": "acfqp:cross-domain-lmb-permutation:v1",
    "transplant": "acfqp:cross-domain-lmb-transplant:v1",
    "calibration": "acfqp:cross-domain-lmb-calibration:v1",
    "randomness_assumption": (
        "acfqp:cross-domain-lmb-randomness-assumption:v1"
    ),
    "campaign": "acfqp:cross-domain-lmb-campaign:v1",
    "verification": "acfqp:cross-domain-lmb-verification:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("cross-domain LMB content domains must be unique")


class CrossDomainLMBInvariantViolation(ValueError):
    """A skeleton, adapter, observation, model, or certificate is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        encoded = canonical_json_bytes(dict(payload))
        tag = DOMAIN_TAGS[role]
    except (KeyError, TypeError, ValueError) as error:
        raise CrossDomainLMBInvariantViolation(str(error)) from error
    return hashlib.sha256(tag.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise CrossDomainLMBInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _state_doc(state: LMBState) -> dict[str, Any]:
    if type(state) is not LMBState:
        raise CrossDomainLMBInvariantViolation(
            "LMB state runtime type was substituted"
        )
    return {
        "removed_mask": state.removed_mask,
        "buffer": list(state.buffer),
        "status": state.status.value,
    }


def _runtime_shape(claimed: Any, expected: Any, path: str) -> None:
    if type(claimed) is not type(expected):
        raise CrossDomainLMBInvariantViolation(
            f"{path} contains a runtime-type substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise CrossDomainLMBInvariantViolation(f"{path} length changed")
        for index, (left, right) in enumerate(zip(claimed, expected)):
            _runtime_shape(left, right, f"{path}[{index}]")
        return
    if is_dataclass(expected):
        for field in fields(type(expected)):
            _runtime_shape(
                object.__getattribute__(claimed, field.name),
                object.__getattribute__(expected, field.name),
                f"{path}.{field.name}",
            )


@dataclass(frozen=True, slots=True)
class LMBRandomnessAssumptionV1:
    """Registered condition under which the statistical bounds are valid."""

    hash_function: str = "SHA-256"
    counter_output_model: str = (
        "independent_uniform_256_bit_random_oracle_outputs"
    )
    simulator_model: str = (
        "iid_outcomes_conditional_on_fixed_distinct_action_concretizer"
    )
    exact_uniform_method: str = "rejection_sampling_below_power_of_two"
    deterministic_replay: bool = True
    entropy_attestation_present: bool = False
    unconditional_iid_claimed: bool = False
    confidence_semantics: str = (
        "conditional_on_registered_random_oracle_and_iid_simulator_assumption"
    )

    def __post_init__(self) -> None:
        if (
            self.hash_function != "SHA-256"
            or self.counter_output_model
            != "independent_uniform_256_bit_random_oracle_outputs"
            or self.simulator_model
            != (
                "iid_outcomes_conditional_on_fixed_distinct_action_"
                "concretizer"
            )
            or self.exact_uniform_method
            != "rejection_sampling_below_power_of_two"
            or self.deterministic_replay is not True
            or self.entropy_attestation_present is not False
            or self.unconditional_iid_claimed is not False
            or self.confidence_semantics
            != (
                "conditional_on_registered_random_oracle_and_iid_"
                "simulator_assumption"
            )
        ):
            raise CrossDomainLMBInvariantViolation(
                "LMB randomness assumption or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_randomness_assumption.v1",
            "schema_version": SCHEMA_VERSION,
            "hash_function": self.hash_function,
            "counter_output_model": self.counter_output_model,
            "simulator_model": self.simulator_model,
            "exact_uniform_method": self.exact_uniform_method,
            "deterministic_replay": self.deterministic_replay,
            "entropy_attestation_present": self.entropy_attestation_present,
            "unconditional_iid_claimed": self.unconditional_iid_claimed,
            "confidence_semantics": self.confidence_semantics,
        }

    @property
    def assumption_id(self) -> str:
        return _content_id("randomness_assumption", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "assumption_id": self.assumption_id}


def lmb_randomness_assumption_v1() -> LMBRandomnessAssumptionV1:
    return LMBRandomnessAssumptionV1()


def _portable_shape(skeleton: Any) -> tuple[str, str, str]:
    """Validate and normalize the small public portable-skeleton interface.

    The portable module owns the exact runtime class.  Importing it lazily
    keeps this domain arm importable while the independent source arm is
    assembled, but duck-typed substitutes are still rejected.
    """

    try:
        from acfqp.portable_relational_skeleton_v1 import (  # type: ignore
            PortableRelationalSkeletonV1,
        )
    except ImportError as error:  # pragma: no cover - integration guard
        raise CrossDomainLMBInvariantViolation(
            "portable relational skeleton authority is unavailable"
        ) from error
    if type(skeleton) is not PortableRelationalSkeletonV1:
        raise CrossDomainLMBInvariantViolation(
            "LMB arm requires the exact portable skeleton runtime type"
        )
    try:
        skeleton_id = parse_content_id(skeleton.skeleton_id)
        state_rendered = str(skeleton.state_program.rendered)
        action_rendered = str(skeleton.action_program.rendered)
    except (AttributeError, TypeError, ValueError) as error:
        raise CrossDomainLMBInvariantViolation(
            "portable skeleton public shape changed"
        ) from error
    if (
        state_rendered != "cardinality_actions(legal_actions)"
        or action_rendered
        != (
            "cardinality_resources("
            "linked_filter(action_anchor,active_resources))"
        )
    ):
        raise CrossDomainLMBInvariantViolation(
            "portable graph-selected relational skeleton changed"
        )
    return skeleton_id, state_rendered, action_rendered


@dataclass(frozen=True, slots=True)
class LMBSemanticsProfileV1:
    match_arity: int = 3
    capacity: int = 3
    match_before_overflow: bool = True
    action_anchor_semantics: str = "selected_tile"
    resource_semantics: str = "materialized_buffer_tokens"
    relation_candidates: tuple[str, ...] = (
        "all_buffer_tokens",
        "different_type_buffer_tokens",
        "same_type_buffer_tokens",
        "selected_tile_blocker_count",
    )

    def __post_init__(self) -> None:
        if (
            self.match_arity != 3
            or self.capacity != 3
            or self.match_before_overflow is not True
            or self.action_anchor_semantics != "selected_tile"
            or self.resource_semantics != "materialized_buffer_tokens"
            or self.relation_candidates
            != (
                "all_buffer_tokens",
                "different_type_buffer_tokens",
                "same_type_buffer_tokens",
                "selected_tile_blocker_count",
            )
        ):
            raise CrossDomainLMBInvariantViolation(
                "LMB relational semantics profile is unregistered"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_semantics.v1",
            "schema_version": SCHEMA_VERSION,
            "match_arity": self.match_arity,
            "capacity": self.capacity,
            "match_before_overflow": self.match_before_overflow,
            "action_anchor_semantics": self.action_anchor_semantics,
            "resource_semantics": self.resource_semantics,
            "relation_candidates": list(self.relation_candidates),
            "primitive_invention_claimed": False,
            "automatic_ontology_alignment_claimed": False,
        }

    @property
    def semantics_id(self) -> str:
        return _content_id("semantics", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "semantics_id": self.semantics_id}


LMB_SEMANTICS = LMBSemanticsProfileV1()


_FIXTURE_SPECS: tuple[
    tuple[
        str,
        tuple[int, ...],
        tuple[tuple[int, ...], ...],
        int,
        tuple[int, int],
        int,
        int,
    ],
    ...,
] = (
    (
        "lmb_cross_domain_seed0_mask7_v0",
        (0, 1, 0, 1, 1, 0),
        ((), (0,), (0,), (0,), (1, 3), (0, 1)),
        7,
        (2, 1),
        5,
        3,
    ),
    (
        "lmb_cross_domain_seed1_mask7_v0",
        (1, 1, 0, 0, 1, 0),
        ((), (), (), (0, 2), (1,), (2,)),
        7,
        (1, 2),
        4,
        3,
    ),
    (
        "lmb_cross_domain_seed4_mask21_v0",
        (1, 0, 0, 0, 1, 1),
        ((2, 4), (), (4,), (4,), (), ()),
        21,
        (1, 2),
        5,
        1,
    ),
)


@dataclass(frozen=True, slots=True)
class LMBTargetContextV1:
    context_key: str
    tile_types: tuple[int, ...]
    blockers: tuple[tuple[int, ...], ...]
    root_removed_mask: int
    root_buffer: tuple[int, int]
    selected_root_tile: int
    expected_continuation_tile: int
    semantics_id: str = LMB_SEMANTICS.semantics_id
    horizon: int = HORIZON
    risk_tolerance: Fraction = RISK_TOLERANCE
    regret_tolerance: Fraction = REGRET_TOLERANCE
    reward_normalizer: Fraction = REWARD_NORMALIZER

    def __post_init__(self) -> None:
        _cid(self.semantics_id, "LMB context semantics")
        if (
            (
                self.context_key,
                self.tile_types,
                self.blockers,
                self.root_removed_mask,
                self.root_buffer,
                self.selected_root_tile,
                self.expected_continuation_tile,
            )
            not in _FIXTURE_SPECS
            or self.semantics_id != LMB_SEMANTICS.semantics_id
            or self.horizon != 2
            or self.risk_tolerance != Fraction(1, 20)
            or self.regret_tolerance != Fraction(1, 20)
            or self.reward_normalizer != 2
        ):
            raise CrossDomainLMBInvariantViolation(
                "held-out LMB context is outside the registered family"
            )
        # The exact kernel is used here only as a structural validation
        # authority, before any query execution.
        kernel = self.kernel()
        root = self.root_state
        legal = kernel.actions(root)
        selected = LMBAction(self.selected_root_tile)
        if (
            selected not in legal
            or root.buffer[kernel.tile_types[selected.tile]] != 2
            or any(
                root.buffer[kernel.tile_types[action.tile]] != 1
                for action in legal
                if action != selected
            )
        ):
            raise CrossDomainLMBInvariantViolation(
                "held-out root does not have the registered support split"
            )

    def kernel(self) -> LMBKernel:
        return LMBKernel(
            self.tile_types,
            tuple(frozenset(item) for item in self.blockers),
            2,
            3,
            3,
        )

    @property
    def root_state(self) -> LMBState:
        return LMBState(
            self.root_removed_mask,
            self.root_buffer,
            LMBStatus.ACTIVE,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_context.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_key": self.context_key,
            "tile_types": list(self.tile_types),
            "blockers": [list(item) for item in self.blockers],
            "type_count": 2,
            "capacity": 3,
            "max_layers": 3,
            "root_state": _state_doc(self.root_state),
            "semantics_id": self.semantics_id,
            "horizon": self.horizon,
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "regret_tolerance": _fdoc(self.regret_tolerance),
            "reward_weights": {"match": 1, "terminal_clear": 0},
            "reward_normalizer": _fdoc(self.reward_normalizer),
            "normalizer_proof": "match_count_le_horizon_v1",
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def registered_lmb_target_contexts_v1() -> tuple[LMBTargetContextV1, ...]:
    return tuple(
        LMBTargetContextV1(*spec)
        for spec in _FIXTURE_SPECS
    )


@dataclass(frozen=True, slots=True)
class LMBBridgeRowV1:
    state: LMBState
    legal_tiles: tuple[int, ...]
    action_tile: int
    tile_type: int
    blocker_count: int
    next_state: LMBState
    match_reward: int
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        if (
            type(self.state) is not LMBState
            or type(self.legal_tiles) is not tuple
            or any(type(item) is not int for item in self.legal_tiles)
            or self.legal_tiles != tuple(sorted(set(self.legal_tiles)))
            or type(self.action_tile) is not int
            or self.action_tile not in self.legal_tiles
            or type(self.tile_type) is not int
            or self.tile_type not in (0, 1)
            or type(self.blocker_count) is not int
            or self.blocker_count < 0
            or type(self.next_state) is not LMBState
            or self.match_reward not in (0, 1)
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or (self.failure and not self.terminal)
        ):
            raise CrossDomainLMBInvariantViolation(
                "query-neutral LMB bridge row is invalid"
            )

    @property
    def state_action_count(self) -> int:
        return len(self.legal_tiles)

    @property
    def same_type_buffer_count(self) -> int:
        return self.state.buffer[self.tile_type]

    @property
    def different_type_buffer_count(self) -> int:
        return sum(self.state.buffer) - self.same_type_buffer_count

    def binding_value(self, binding_key: str) -> int:
        return {
            "all_buffer_tokens": sum(self.state.buffer),
            "different_type_buffer_tokens": (
                self.different_type_buffer_count
            ),
            "same_type_buffer_tokens": self.same_type_buffer_count,
            "selected_tile_blocker_count": self.blocker_count,
        }[binding_key]

    @property
    def outcome_signature(self) -> tuple[Any, ...]:
        return (
            self.match_reward,
            self.failure,
            self.terminal,
            self.next_state.status.value,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_bridge_row.v1",
            "schema_version": SCHEMA_VERSION,
            "state": _state_doc(self.state),
            "legal_tiles": list(self.legal_tiles),
            "action_tile": self.action_tile,
            "tile_type": self.tile_type,
            "blocker_count": self.blocker_count,
            "next_state": _state_doc(self.next_state),
            "match_reward": self.match_reward,
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def row_id(self) -> str:
        return _content_id("bridge_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class LMBBridgeLogV1:
    semantics_id: str
    rows: tuple[LMBBridgeRowV1, ...]
    query_inputs_used: int = 0
    heldout_target_inputs_used: int = 0
    policy_value_inputs_used: int = 0

    def __post_init__(self) -> None:
        _cid(self.semantics_id, "bridge semantics")
        if (
            self.semantics_id != LMB_SEMANTICS.semantics_id
            or type(self.rows) is not tuple
            or len(self.rows) != 7
            or any(type(item) is not LMBBridgeRowV1 for item in self.rows)
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or self.query_inputs_used != 0
            or self.heldout_target_inputs_used != 0
            or self.policy_value_inputs_used != 0
        ):
            raise CrossDomainLMBInvariantViolation(
                "query-neutral bridge log changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_bridge_log.v1",
            "schema_version": SCHEMA_VERSION,
            "semantics_id": self.semantics_id,
            "rows": [item.to_document() for item in self.rows],
            "query_inputs_used": self.query_inputs_used,
            "heldout_target_inputs_used": (
                self.heldout_target_inputs_used
            ),
            "policy_value_inputs_used": self.policy_value_inputs_used,
        }

    @property
    def bridge_log_id(self) -> str:
        return _content_id("bridge_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "bridge_log_id": self.bridge_log_id}


def query_neutral_lmb_bridge_log_v1() -> LMBBridgeLogV1:
    """Materialize the frozen seven-row bridge without an old V0-058 producer."""

    kernel = LMBKernel(
        (0, 1, 0, 1, 1, 0),
        (
            frozenset(),
            frozenset(),
            frozenset((0, 1)),
            frozenset((0, 1)),
            frozenset((0, 1)),
            frozenset((0, 1)),
        ),
        2,
        3,
        2,
    )
    states_and_tiles = (
        (LMBState(7, (2, 1)), 3),
        (LMBState(9, (1, 1)), 1),
        (LMBState(31, (2, 0)), 5),
        (LMBState(34, (1, 1)), 0),
        (LMBState(36, (2, 0)), 0),
        (LMBState(37, (0, 0)), 1),
        (LMBState(52, (2, 1)), 1),
    )
    rows: list[LMBBridgeRowV1] = []
    for state, tile in states_and_tiles:
        legal = kernel.actions(state)
        action = LMBAction(tile)
        if action not in legal:
            raise CrossDomainLMBInvariantViolation(
                "literal bridge action is no longer legal"
            )
        outcome = kernel.step(state, action)[0]
        rows.append(
            LMBBridgeRowV1(
                state,
                tuple(item.tile for item in legal),
                tile,
                kernel.tile_types[tile],
                len(kernel.blockers[tile]),
                outcome.next_state,
                int(dict(outcome.reward_features).get("match", 0)),
                outcome.failure,
                outcome.terminal,
            )
        )
    return LMBBridgeLogV1(
        LMB_SEMANTICS.semantics_id,
        tuple(sorted(rows, key=lambda item: item.row_id)),
    )


@dataclass(frozen=True, slots=True)
class LMBBindingCandidateV1:
    binding_key: str
    observed_alias_conflict_count: int
    abstract_support_count: int
    observed_values: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            self.binding_key not in LMB_SEMANTICS.relation_candidates
            or type(self.observed_alias_conflict_count) is not int
            or self.observed_alias_conflict_count < 0
            or type(self.abstract_support_count) is not int
            or self.abstract_support_count <= 0
            or type(self.observed_values) is not tuple
            or not self.observed_values
            or self.observed_values
            != tuple(sorted(set(self.observed_values)))
        ):
            raise CrossDomainLMBInvariantViolation(
                "LMB slot-binding candidate is invalid"
            )

    @property
    def selection_key(self) -> tuple[Any, ...]:
        return (
            self.observed_alias_conflict_count,
            self.abstract_support_count,
            LMB_SEMANTICS.relation_candidates.index(self.binding_key),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_binding_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "binding_key": self.binding_key,
            "observed_alias_conflict_count": (
                self.observed_alias_conflict_count
            ),
            "abstract_support_count": self.abstract_support_count,
            "observed_values": list(self.observed_values),
        }

    @property
    def candidate_id(self) -> str:
        return _content_id("binding_candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class LMBSlotBindingV1:
    skeleton_id: str
    semantics_id: str
    bridge_log_id: str
    candidates: tuple[LMBBindingCandidateV1, ...]
    selected_candidate_id: str
    selected_binding_key: str
    state_program_rendered: str
    action_program_rendered: str
    complete_binding_search: bool = True
    query_inputs_used: int = 0
    heldout_target_inputs_used: int = 0
    target_transition_inputs_used: int = 0
    automatic_ontology_alignment_claimed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.skeleton_id, "binding skeleton"),
            (self.semantics_id, "binding semantics"),
            (self.bridge_log_id, "binding bridge log"),
            (self.selected_candidate_id, "selected binding candidate"),
        ):
            _cid(value, field)
        if (
            self.semantics_id != LMB_SEMANTICS.semantics_id
            or type(self.candidates) is not tuple
            or len(self.candidates) != 4
            or any(
                type(item) is not LMBBindingCandidateV1
                for item in self.candidates
            )
            or tuple(item.binding_key for item in self.candidates)
            != LMB_SEMANTICS.relation_candidates
            or self.selected_candidate_id
            not in {item.candidate_id for item in self.candidates}
            or self.selected_binding_key != "same_type_buffer_tokens"
            or next(
                item
                for item in self.candidates
                if item.candidate_id == self.selected_candidate_id
            ).binding_key
            != self.selected_binding_key
            or self.complete_binding_search is not True
            or any(
                value != 0
                for value in (
                    self.query_inputs_used,
                    self.heldout_target_inputs_used,
                    self.target_transition_inputs_used,
                )
            )
            or self.automatic_ontology_alignment_claimed is not False
        ):
            raise CrossDomainLMBInvariantViolation(
                "LMB slot binding or claim boundary changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_slot_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "skeleton_id": self.skeleton_id,
            "semantics_id": self.semantics_id,
            "bridge_log_id": self.bridge_log_id,
            "candidates": [item.to_document() for item in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
            "selected_binding_key": self.selected_binding_key,
            "state_program_rendered": self.state_program_rendered,
            "action_program_rendered": self.action_program_rendered,
            "complete_binding_search": self.complete_binding_search,
            "query_inputs_used": self.query_inputs_used,
            "heldout_target_inputs_used": self.heldout_target_inputs_used,
            "target_transition_inputs_used": (
                self.target_transition_inputs_used
            ),
            "automatic_ontology_alignment_claimed": (
                self.automatic_ontology_alignment_claimed
            ),
        }

    @property
    def binding_id(self) -> str:
        return _content_id("binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "binding_id": self.binding_id}


def bind_lmb_relational_slot_v1(
    skeleton: Any,
    bridge_log: LMBBridgeLogV1,
) -> LMBSlotBindingV1:
    skeleton_id, state_rendered, action_rendered = _portable_shape(skeleton)
    if (
        type(bridge_log) is not LMBBridgeLogV1
        or bridge_log != query_neutral_lmb_bridge_log_v1()
    ):
        raise CrossDomainLMBInvariantViolation(
            "slot binding requires the frozen query-neutral bridge log"
        )
    candidates: list[LMBBindingCandidateV1] = []
    for binding_key in LMB_SEMANTICS.relation_candidates:
        signatures: dict[tuple[int, int], set[tuple[Any, ...]]] = {}
        observed_values: set[int] = set()
        for row in bridge_log.rows:
            value = row.binding_value(binding_key)
            observed_values.add(value)
            signatures.setdefault(
                (row.state_action_count, value),
                set(),
            ).add(row.outcome_signature)
        conflicts = sum(
            len(values) - 1
            for values in signatures.values()
            if len(values) > 1
        )
        candidates.append(
            LMBBindingCandidateV1(
                binding_key,
                conflicts,
                len(signatures),
                tuple(sorted(observed_values)),
            )
        )
    ordered = tuple(
        next(item for item in candidates if item.binding_key == key)
        for key in LMB_SEMANTICS.relation_candidates
    )
    selected = min(ordered, key=lambda item: item.selection_key)
    if selected.binding_key != "same_type_buffer_tokens":
        raise CrossDomainLMBInvariantViolation(
            "bridge observations no longer select same-type buffer support"
        )
    return LMBSlotBindingV1(
        skeleton_id,
        LMB_SEMANTICS.semantics_id,
        bridge_log.bridge_log_id,
        ordered,
        selected.candidate_id,
        selected.binding_key,
        state_rendered,
        action_rendered,
    )


def materialize_lmb_relational_state_v1(
    context: LMBTargetContextV1,
    state: LMBState,
    remaining_horizon: int,
    binding: LMBSlotBindingV1,
) -> Any:
    """Compile one LMB state into the shared portable relational IR.

    Tile nodes occupy resource IDs ``0..5``.  Four possible buffer-token
    nodes follow, two for each tile type.  The relation binding changes only
    ``linked_pairs``; no transition outcome is consulted.
    """

    from acfqp.portable_relational_skeleton_v1 import (
        RelationalActionSlotV1,
        RelationalStateIRV1,
    )

    if (
        type(context) is not LMBTargetContextV1
        or type(state) is not LMBState
        or type(binding) is not LMBSlotBindingV1
        or binding.semantics_id != context.semantics_id
        or type(remaining_horizon) is not int
        or not 0 <= remaining_horizon <= HORIZON
    ):
        raise CrossDomainLMBInvariantViolation(
            "LMB relational materialization binding is invalid"
        )
    kernel = context.kernel()
    if len(state.buffer) != 2:
        raise CrossDomainLMBInvariantViolation(
            "LMB relational materialization requires two buffer types"
        )
    token_type = (0, 0, 1, 1)
    token_nodes = tuple(range(6, 10))
    active_tokens = tuple(
        token_nodes[2 * tile_type + ordinal]
        for tile_type, count in enumerate(state.buffer)
        for ordinal in range(count)
    )
    legal = (
        kernel.actions(state)
        if remaining_horizon > 0 and state.status is LMBStatus.ACTIVE
        else ()
    )
    actions = tuple(
        sorted(
            (
                RelationalActionSlotV1(f"tile={item.tile}", item.tile)
                for item in legal
            ),
            key=lambda item: item.action_slot_id,
        )
    )
    if binding.selected_binding_key == "same_type_buffer_tokens":
        linked = tuple(
            sorted(
                (tile, node)
                for tile, tile_type in enumerate(context.tile_types)
                for node, resource_type in zip(token_nodes, token_type)
                if tile_type == resource_type
            )
        )
    elif binding.selected_binding_key == "different_type_buffer_tokens":
        linked = tuple(
            sorted(
                (tile, node)
                for tile, tile_type in enumerate(context.tile_types)
                for node, resource_type in zip(token_nodes, token_type)
                if tile_type != resource_type
            )
        )
    elif binding.selected_binding_key == "all_buffer_tokens":
        linked = tuple(
            (tile, node)
            for tile in range(6)
            for node in token_nodes
        )
    elif binding.selected_binding_key == "selected_tile_blocker_count":
        linked = tuple(
            sorted(
                (tile, blocker)
                for tile, blockers in enumerate(context.blockers)
                for blocker in blockers
            )
        )
    else:  # pragma: no cover - exact binding class prevents this
        raise CrossDomainLMBInvariantViolation(
            "LMB relation binding is unregistered"
        )
    terminal_kind = {
        LMBStatus.ACTIVE: (
            "HORIZON_TERMINAL"
            if remaining_horizon == 0
            else "ACTIVE"
        ),
        LMBStatus.SUCCESS: "SUCCESS",
        LMBStatus.FAILURE: "FAILURE",
    }[state.status]
    return RelationalStateIRV1(
        context.context_id,
        remaining_horizon,
        tuple((*context.tile_types, *token_type)),
        tuple(range(6)) + active_tokens,
        linked,
        actions,
        terminal_kind,
    )


def evaluate_bound_lmb_coordinates_v1(
    skeleton: Any,
    binding: LMBSlotBindingV1,
    context: LMBTargetContextV1,
    state: LMBState,
    remaining_horizon: int,
) -> tuple[int, tuple[tuple[int, int], ...]]:
    from acfqp.portable_relational_skeleton_v1 import (
        evaluate_portable_action_program_v1,
        evaluate_portable_state_program_v1,
    )

    skeleton_id, *_ = _portable_shape(skeleton)
    if (
        type(binding) is not LMBSlotBindingV1
        or binding.skeleton_id != skeleton_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "bound coordinate evaluation received a stale skeleton"
        )
    state_ir = materialize_lmb_relational_state_v1(
        context,
        state,
        remaining_horizon,
        binding,
    )
    state_value = evaluate_portable_state_program_v1(
        skeleton.state_program,
        state_ir,
    )
    if state_value[0] != "INTEGER":
        raise CrossDomainLMBInvariantViolation(
            "portable LMB state coordinate is not integer"
        )
    action_values: list[tuple[int, int]] = []
    for action in state_ir.legal_actions:
        tagged = evaluate_portable_action_program_v1(
            skeleton.action_program,
            state_ir,
            action,
        )
        if tagged[0] != "INTEGER":
            raise CrossDomainLMBInvariantViolation(
                "portable LMB action coordinate is not integer"
            )
        action_values.append(
            (
                int(action.opaque_action_key.removeprefix("tile=")),
                int(tagged[1]),
            )
        )
    return int(state_value[1]), tuple(sorted(action_values))


@dataclass(frozen=True, slots=True)
class LMBSemanticSupportV1:
    skeleton_id: str
    binding_id: str
    context_id: str
    state: LMBState
    remaining_horizon: int
    state_coordinate: int
    action_coordinate: int
    ground_action_tiles: tuple[int, ...]
    concretizer_kind: str = "uniform_over_distinct_ground_actions_v1"

    def __post_init__(self) -> None:
        for value, field in (
            (self.skeleton_id, "support skeleton"),
            (self.binding_id, "support binding"),
            (self.context_id, "support context"),
        ):
            _cid(value, field)
        if (
            type(self.state) is not LMBState
            or self.state.status is not LMBStatus.ACTIVE
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, 2)
            or type(self.state_coordinate) is not int
            or self.state_coordinate <= 0
            or type(self.action_coordinate) is not int
            or self.action_coordinate not in (1, 2)
            or type(self.ground_action_tiles) is not tuple
            or not self.ground_action_tiles
            or self.ground_action_tiles
            != tuple(sorted(set(self.ground_action_tiles)))
            or self.concretizer_kind
            != "uniform_over_distinct_ground_actions_v1"
        ):
            raise CrossDomainLMBInvariantViolation(
                "LMB semantic support is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_support.v1",
            "schema_version": SCHEMA_VERSION,
            "skeleton_id": self.skeleton_id,
            "binding_id": self.binding_id,
            "context_id": self.context_id,
            "state": _state_doc(self.state),
            "remaining_horizon": self.remaining_horizon,
            "state_coordinate": self.state_coordinate,
            "action_coordinate": self.action_coordinate,
            "ground_action_tiles": list(self.ground_action_tiles),
            "concretizer_kind": self.concretizer_kind,
        }

    @property
    def support_id(self) -> str:
        return _content_id("support", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_id": self.support_id}


def semantic_support_v1(
    skeleton: Any,
    binding: LMBSlotBindingV1,
    context: LMBTargetContextV1,
    state: LMBState,
    remaining_horizon: int,
    action_coordinate: int,
) -> LMBSemanticSupportV1:
    state_coordinate, rows = evaluate_bound_lmb_coordinates_v1(
        skeleton,
        binding,
        context,
        state,
        remaining_horizon,
    )
    actions = tuple(
        tile for tile, value in rows if value == action_coordinate
    )
    if not actions:
        raise CrossDomainLMBInvariantViolation(
            "requested LMB semantic action has empty support"
        )
    return LMBSemanticSupportV1(
        binding.skeleton_id,
        binding.binding_id,
        context.context_id,
        state,
        remaining_horizon,
        state_coordinate,
        action_coordinate,
        actions,
    )


class LMBAuditOutcome(str, Enum):
    FAILED_MISSING_ROOT_SUPPORT = "FAILED_MISSING_ROOT_SUPPORT"
    FAILED_MISSING_CONTINUATION_SUPPORT = (
        "FAILED_MISSING_CONTINUATION_SUPPORT"
    )
    CERTIFIED = "CERTIFIED"
    FAILED_NO_SOUND_ACTION = "FAILED_NO_SOUND_ACTION"


@dataclass(frozen=True, slots=True)
class LMBStatisticalModelRowV1:
    support: LMBSemanticSupportV1
    trace_id: str
    empirical_reward: Fraction
    empirical_failure: Fraction
    empirical_active: Fraction
    empirical_horizon_terminal: Fraction
    reward_lower: Fraction
    reward_upper: Fraction
    failure_lower: Fraction
    failure_upper: Fraction
    active_lower: Fraction
    active_upper: Fraction
    horizon_lower: Fraction
    horizon_upper: Fraction
    revealed_active_state: LMBState | None

    def __post_init__(self) -> None:
        if type(self.support) is not LMBSemanticSupportV1:
            raise CrossDomainLMBInvariantViolation(
                "model row support runtime type changed"
            )
        _cid(self.trace_id, "model row trace")
        values = (
            self.empirical_reward,
            self.empirical_failure,
            self.empirical_active,
            self.empirical_horizon_terminal,
            self.reward_lower,
            self.reward_upper,
            self.failure_lower,
            self.failure_upper,
            self.active_lower,
            self.active_upper,
            self.horizon_lower,
            self.horizon_upper,
        )
        if (
            any(type(item) is not Fraction for item in values)
            or any(not 0 <= item <= 1 for item in values)
            or not (
                self.reward_lower
                <= self.empirical_reward
                <= self.reward_upper
            )
            or not (
                self.failure_lower
                <= self.empirical_failure
                <= self.failure_upper
            )
            or not (
                self.active_lower
                <= self.empirical_active
                <= self.active_upper
            )
            or not (
                self.horizon_lower
                <= self.empirical_horizon_terminal
                <= self.horizon_upper
            )
            or (
                self.revealed_active_state is not None
                and (
                    type(self.revealed_active_state) is not LMBState
                    or self.revealed_active_state.status
                    is not LMBStatus.ACTIVE
                )
            )
        ):
            raise CrossDomainLMBInvariantViolation(
                "statistical model row interval is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_model_row.v1",
            "schema_version": SCHEMA_VERSION,
            "support": self.support.to_document(),
            "trace_id": self.trace_id,
            "empirical": {
                "reward": _fdoc(self.empirical_reward),
                "failure": _fdoc(self.empirical_failure),
                "active": _fdoc(self.empirical_active),
                "horizon_terminal": _fdoc(
                    self.empirical_horizon_terminal
                ),
            },
            "interval": {
                "reward": [
                    _fdoc(self.reward_lower),
                    _fdoc(self.reward_upper),
                ],
                "failure": [
                    _fdoc(self.failure_lower),
                    _fdoc(self.failure_upper),
                ],
                "active": [
                    _fdoc(self.active_lower),
                    _fdoc(self.active_upper),
                ],
                "horizon_terminal": [
                    _fdoc(self.horizon_lower),
                    _fdoc(self.horizon_upper),
                ],
            },
            "revealed_active_state": (
                None
                if self.revealed_active_state is None
                else _state_doc(self.revealed_active_state)
            ),
        }

    @property
    def row_id(self) -> str:
        return _content_id("model_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class LMBPartialStatisticalRAPMV1:
    skeleton_id: str
    binding_id: str
    context_id: str
    epoch_index: int
    parent_model_id: str | None
    rows: tuple[LMBStatisticalModelRowV1, ...]
    source_dynamics_imported: bool = False
    exact_target_rows_enumerated: int = 0
    target_program_generation_count: int = 0
    source_frozen_refinement_registry_used: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.skeleton_id, "model skeleton"),
            (self.binding_id, "model binding"),
            (self.context_id, "model context"),
        ):
            _cid(value, field)
        if self.parent_model_id is not None:
            _cid(self.parent_model_id, "model parent")
        if (
            type(self.epoch_index) is not int
            or self.epoch_index not in (0, 1, 2)
            or (self.epoch_index == 0) != (self.parent_model_id is None)
            or type(self.rows) is not tuple
            or len(self.rows) != self.epoch_index
            or any(
                type(item) is not LMBStatisticalModelRowV1
                or item.support.skeleton_id != self.skeleton_id
                or item.support.binding_id != self.binding_id
                or item.support.context_id != self.context_id
                for item in self.rows
            )
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or self.source_dynamics_imported is not False
            or self.exact_target_rows_enumerated != 0
            or self.target_program_generation_count != 0
            or self.source_frozen_refinement_registry_used is not False
        ):
            raise CrossDomainLMBInvariantViolation(
                "partial statistical RAPM chronology or claim changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_partial_statistical_rapm.v1",
            "schema_version": SCHEMA_VERSION,
            "skeleton_id": self.skeleton_id,
            "binding_id": self.binding_id,
            "context_id": self.context_id,
            "epoch_index": self.epoch_index,
            "parent_model_id": self.parent_model_id,
            "rows": [item.to_document() for item in self.rows],
            "source_dynamics_imported": self.source_dynamics_imported,
            "exact_target_rows_enumerated": (
                self.exact_target_rows_enumerated
            ),
            "target_program_generation_count": (
                self.target_program_generation_count
            ),
            "source_frozen_refinement_registry_used": (
                self.source_frozen_refinement_registry_used
            ),
        }

    @property
    def model_id(self) -> str:
        return _content_id("model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}


def initial_lmb_partial_statistical_rapm_v1(
    binding: LMBSlotBindingV1,
    context: LMBTargetContextV1,
) -> LMBPartialStatisticalRAPMV1:
    if (
        type(binding) is not LMBSlotBindingV1
        or type(context) is not LMBTargetContextV1
        or binding.semantics_id != context.semantics_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "initial LMB RAPM identity binding is invalid"
        )
    return LMBPartialStatisticalRAPMV1(
        binding.skeleton_id,
        binding.binding_id,
        context.context_id,
        0,
        None,
        (),
    )


@dataclass(frozen=True, slots=True)
class LMBSoundAuditV1:
    skeleton_id: str
    binding_id: str
    context_id: str
    model_id: str
    outcome: LMBAuditOutcome
    missing_support: LMBSemanticSupportV1 | None
    selected_root_action_coordinate: int
    selected_continuation_action_coordinate: int | None
    root_action_catalogue: tuple[int, ...]
    continuation_action_catalogue: tuple[int, ...]
    reward_lower: Fraction
    reward_upper: Fraction
    unrestricted_reward_upper: Fraction
    failure_upper: Fraction
    normalized_regret_upper: Fraction
    selector_profile: str = (
        "enumerated_semantic_catalogue_structural_rank_tiebreak_v1"
    )
    randomness_assumption_id: str = (
        lmb_randomness_assumption_v1().assumption_id
    )
    statistical_confidence_conditional: bool = True
    unconditional_iid_claimed: bool = False
    target_transition_calls: int = 0
    exact_ground_rows_used: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.skeleton_id, "audit skeleton"),
            (self.binding_id, "audit binding"),
            (self.context_id, "audit context"),
            (self.model_id, "audit model"),
            (self.randomness_assumption_id, "audit randomness assumption"),
        ):
            _cid(value, field)
        values = (
            self.reward_lower,
            self.reward_upper,
            self.unrestricted_reward_upper,
            self.failure_upper,
            self.normalized_regret_upper,
        )
        if (
            type(self.outcome) is not LMBAuditOutcome
            or (
                self.missing_support is not None
                and type(self.missing_support) is not LMBSemanticSupportV1
            )
            or (
                self.outcome is LMBAuditOutcome.CERTIFIED
                and self.missing_support is not None
            )
            or (
                self.outcome
                in (
                    LMBAuditOutcome.FAILED_MISSING_ROOT_SUPPORT,
                    LMBAuditOutcome.FAILED_MISSING_CONTINUATION_SUPPORT,
                )
                and self.missing_support is None
            )
            or type(self.root_action_catalogue) is not tuple
            or not self.root_action_catalogue
            or self.root_action_catalogue
            != tuple(sorted(set(self.root_action_catalogue)))
            or self.selected_root_action_coordinate
            not in self.root_action_catalogue
            or type(self.continuation_action_catalogue) is not tuple
            or self.continuation_action_catalogue
            != tuple(sorted(set(self.continuation_action_catalogue)))
            or (
                self.outcome
                in (
                    LMBAuditOutcome.FAILED_MISSING_CONTINUATION_SUPPORT,
                    LMBAuditOutcome.CERTIFIED,
                )
                and (
                    not self.continuation_action_catalogue
                    or self.selected_continuation_action_coordinate
                    not in self.continuation_action_catalogue
                )
            )
            or (
                self.outcome is LMBAuditOutcome.FAILED_MISSING_ROOT_SUPPORT
                and (
                    self.selected_continuation_action_coordinate is not None
                    or self.continuation_action_catalogue
                )
            )
            or self.selector_profile
            != "enumerated_semantic_catalogue_structural_rank_tiebreak_v1"
            or self.randomness_assumption_id
            != lmb_randomness_assumption_v1().assumption_id
            or self.statistical_confidence_conditional is not True
            or self.unconditional_iid_claimed is not False
            or any(type(item) is not Fraction or item < 0 for item in values)
            or self.reward_lower > self.reward_upper
            or self.reward_upper > self.unrestricted_reward_upper
            or self.target_transition_calls != 0
            or self.exact_ground_rows_used != 0
        ):
            raise CrossDomainLMBInvariantViolation(
                "LMB sound audit is malformed or used ground authority"
            )
        if self.outcome is LMBAuditOutcome.CERTIFIED and (
            self.failure_upper >= RISK_TOLERANCE
            or self.normalized_regret_upper >= REGRET_TOLERANCE
        ):
            raise CrossDomainLMBInvariantViolation(
                "certified LMB audit exceeds a registered threshold"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "skeleton_id": self.skeleton_id,
            "binding_id": self.binding_id,
            "context_id": self.context_id,
            "model_id": self.model_id,
            "outcome": self.outcome.value,
            "missing_support": (
                None
                if self.missing_support is None
                else self.missing_support.to_document()
            ),
            "selected_root_action_coordinate": (
                self.selected_root_action_coordinate
            ),
            "selected_continuation_action_coordinate": (
                self.selected_continuation_action_coordinate
            ),
            "root_action_catalogue": list(self.root_action_catalogue),
            "continuation_action_catalogue": list(
                self.continuation_action_catalogue
            ),
            "selector_profile": self.selector_profile,
            "randomness_assumption_id": self.randomness_assumption_id,
            "statistical_confidence_conditional": (
                self.statistical_confidence_conditional
            ),
            "unconditional_iid_claimed": self.unconditional_iid_claimed,
            "bounds": {
                "reward_lower": _fdoc(self.reward_lower),
                "reward_upper": _fdoc(self.reward_upper),
                "unrestricted_reward_upper": _fdoc(
                    self.unrestricted_reward_upper
                ),
                "failure_upper": _fdoc(self.failure_upper),
                "normalized_regret_upper": _fdoc(
                    self.normalized_regret_upper
                ),
            },
            "target_transition_calls": self.target_transition_calls,
            "exact_ground_rows_used": self.exact_ground_rows_used,
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


def _row_by_horizon(
    model: LMBPartialStatisticalRAPMV1,
    remaining_horizon: int,
) -> LMBStatisticalModelRowV1 | None:
    return next(
        (
            item
            for item in model.rows
            if item.support.remaining_horizon == remaining_horizon
        ),
        None,
    )


def _enumerated_semantic_action_catalogue_v1(
    skeleton: Any,
    binding: LMBSlotBindingV1,
    context: LMBTargetContextV1,
    state: LMBState,
    remaining_horizon: int,
) -> tuple[int, ...]:
    _, action_values = evaluate_bound_lmb_coordinates_v1(
        skeleton,
        binding,
        context,
        state,
        remaining_horizon,
    )
    catalogue = tuple(sorted({value for _, value in action_values}))
    if not catalogue:
        raise CrossDomainLMBInvariantViolation(
            "semantic action catalogue is empty"
        )
    return catalogue


def _symbolic_semantic_action_rank_v1(
    state: LMBState,
    action_coordinate: int,
) -> tuple[int, int, int]:
    """Frozen model-only rank: failure, negative reward, tie-break."""

    if (
        type(state) is not LMBState
        or state.status is not LMBStatus.ACTIVE
        or type(action_coordinate) is not int
        or not 0 <= action_coordinate < LMB_SEMANTICS.match_arity
    ):
        raise CrossDomainLMBInvariantViolation(
            "semantic selector input is outside the registered adapter"
        )
    matched = action_coordinate + 1 == LMB_SEMANTICS.match_arity
    next_occupancy = (
        sum(state.buffer) - action_coordinate
        if matched
        else sum(state.buffer) + 1
    )
    failure = next_occupancy > LMB_SEMANTICS.capacity
    # Larger coordinates are the frozen final tie-break only after symbolic
    # failure and immediate match reward agree.
    return int(failure), -int(matched), -action_coordinate


def _select_semantic_action_v1(
    state: LMBState,
    catalogue: tuple[int, ...],
) -> int:
    if (
        type(catalogue) is not tuple
        or not catalogue
        or catalogue != tuple(sorted(set(catalogue)))
    ):
        raise CrossDomainLMBInvariantViolation(
            "semantic selector requires a complete canonical catalogue"
        )
    return min(
        catalogue,
        key=lambda value: _symbolic_semantic_action_rank_v1(state, value),
    )


def audit_lmb_partial_statistical_rapm_v1(
    skeleton: Any,
    binding: LMBSlotBindingV1,
    context: LMBTargetContextV1,
    model: LMBPartialStatisticalRAPMV1,
) -> LMBSoundAuditV1:
    skeleton_id, *_ = _portable_shape(skeleton)
    if (
        type(binding) is not LMBSlotBindingV1
        or type(context) is not LMBTargetContextV1
        or type(model) is not LMBPartialStatisticalRAPMV1
        or binding.skeleton_id != skeleton_id
        or model.skeleton_id != skeleton_id
        or model.binding_id != binding.binding_id
        or model.context_id != context.context_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "LMB model-only audit identity chain is invalid"
        )
    root_catalogue = _enumerated_semantic_action_catalogue_v1(
        skeleton,
        binding,
        context,
        context.root_state,
        2,
    )
    selected_root = _select_semantic_action_v1(
        context.root_state,
        root_catalogue,
    )
    root_support = semantic_support_v1(
        skeleton,
        binding,
        context,
        context.root_state,
        2,
        selected_root,
    )
    root_row = _row_by_horizon(model, 2)
    if root_row is None:
        return LMBSoundAuditV1(
            skeleton_id,
            binding.binding_id,
            context.context_id,
            model.model_id,
            LMBAuditOutcome.FAILED_MISSING_ROOT_SUPPORT,
            root_support,
            selected_root,
            None,
            root_catalogue,
            (),
            Fraction(0),
            Fraction(2),
            Fraction(2),
            Fraction(1),
            Fraction(1),
        )
    if (
        root_row.support.support_id != root_support.support_id
        or root_row.revealed_active_state is None
    ):
        raise CrossDomainLMBInvariantViolation(
            "root statistical row did not reveal the selected continuation"
        )
    continuation_catalogue = _enumerated_semantic_action_catalogue_v1(
        skeleton,
        binding,
        context,
        root_row.revealed_active_state,
        1,
    )
    selected_continuation = _select_semantic_action_v1(
        root_row.revealed_active_state,
        continuation_catalogue,
    )
    continuation_support = semantic_support_v1(
        skeleton,
        binding,
        context,
        root_row.revealed_active_state,
        1,
        selected_continuation,
    )
    continuation_row = _row_by_horizon(model, 1)
    if continuation_row is None:
        return LMBSoundAuditV1(
            skeleton_id,
            binding.binding_id,
            context.context_id,
            model.model_id,
            LMBAuditOutcome.FAILED_MISSING_CONTINUATION_SUPPORT,
            continuation_support,
            selected_root,
            selected_continuation,
            root_catalogue,
            continuation_catalogue,
            root_row.reward_lower,
            root_row.reward_upper + Fraction(1),
            root_row.reward_upper + Fraction(1),
            Fraction(1),
            Fraction(1),
        )
    if continuation_row.support.support_id != continuation_support.support_id:
        raise CrossDomainLMBInvariantViolation(
            "continuation row is outside the revealed proof cone"
        )

    # The complete root catalogue and canonical buffer arithmetic prove every
    # unselected root semantic action is immediately unsafe.
    # This is a structural rule, not a target transition-row lookup.  Hence
    # the unrestricted robust reward upper is attained by the selected root
    # support and its sampled continuation.
    if not _structural_unselected_root_actions_direct_bad(
        context,
        binding,
        skeleton,
    ):
        raise CrossDomainLMBInvariantViolation(
            "registered root structural dominance proof failed"
        )
    reward_lower = root_row.reward_lower + continuation_row.reward_lower
    reward_upper = root_row.reward_upper + continuation_row.reward_upper
    unrestricted_upper = reward_upper
    failure_upper = (
        root_row.failure_upper
        + (1 - root_row.failure_upper)
        * continuation_row.failure_upper
    )
    normalized_regret = (
        unrestricted_upper - reward_lower
    ) / context.reward_normalizer
    return LMBSoundAuditV1(
        skeleton_id,
        binding.binding_id,
        context.context_id,
        model.model_id,
        LMBAuditOutcome.CERTIFIED,
        None,
        selected_root,
        selected_continuation,
        root_catalogue,
        continuation_catalogue,
        reward_lower,
        reward_upper,
        unrestricted_upper,
        failure_upper,
        normalized_regret,
    )


def _structural_unselected_root_actions_direct_bad(
    context: LMBTargetContextV1,
    binding: LMBSlotBindingV1,
    skeleton: Any,
) -> bool:
    root = context.root_state
    kernel = context.kernel()
    _, action_values = evaluate_bound_lmb_coordinates_v1(
        skeleton,
        binding,
        context,
        root,
        2,
    )
    catalogue = tuple(sorted({value for _, value in action_values}))
    selected = _select_semantic_action_v1(root, catalogue)
    unselected = tuple(value for value in catalogue if value != selected)
    if not unselected:
        return False
    for coordinate in unselected:
        if _symbolic_semantic_action_rank_v1(root, coordinate)[0] != 1:
            return False
        tiles = tuple(
            tile for tile, value in action_values if value == coordinate
        )
        if not tiles:
            return False
        for tile in tiles:
            tile_type = kernel.tile_types[tile]
            if root.buffer[tile_type] != coordinate:
                return False
    return True


@dataclass(frozen=True, slots=True)
class LMBSupportAuthorizationV1:
    skeleton_id: str
    binding_id: str
    context_id: str
    model_id: str
    failed_audit_id: str
    support: LMBSemanticSupportV1
    transaction_index: int
    draw_count: int = SAMPLE_COUNT_PER_SUPPORT

    def __post_init__(self) -> None:
        for value, field in (
            (self.skeleton_id, "authorization skeleton"),
            (self.binding_id, "authorization binding"),
            (self.context_id, "authorization context"),
            (self.model_id, "authorization model"),
            (self.failed_audit_id, "authorization audit"),
        ):
            _cid(value, field)
        if (
            type(self.support) is not LMBSemanticSupportV1
            or self.support.skeleton_id != self.skeleton_id
            or self.support.binding_id != self.binding_id
            or self.support.context_id != self.context_id
            or self.transaction_index
            != 3 - self.support.remaining_horizon
            or self.transaction_index not in (1, 2)
            or self.draw_count != SAMPLE_COUNT_PER_SUPPORT
        ):
            raise CrossDomainLMBInvariantViolation(
                "support authorization chronology or cap changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "skeleton_id": self.skeleton_id,
            "binding_id": self.binding_id,
            "context_id": self.context_id,
            "model_id": self.model_id,
            "failed_audit_id": self.failed_audit_id,
            "support": self.support.to_document(),
            "transaction_index": self.transaction_index,
            "draw_count": self.draw_count,
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authorization_id": self.authorization_id}


def authorize_missing_lmb_support_v1(
    audit: LMBSoundAuditV1,
    model: LMBPartialStatisticalRAPMV1,
) -> LMBSupportAuthorizationV1:
    if (
        type(audit) is not LMBSoundAuditV1
        or type(model) is not LMBPartialStatisticalRAPMV1
        or audit.model_id != model.model_id
        or audit.missing_support is None
        or audit.outcome
        not in (
            LMBAuditOutcome.FAILED_MISSING_ROOT_SUPPORT,
            LMBAuditOutcome.FAILED_MISSING_CONTINUATION_SUPPORT,
        )
    ):
        raise CrossDomainLMBInvariantViolation(
            "only an earliest failed proof may authorize LMB evidence"
        )
    return LMBSupportAuthorizationV1(
        audit.skeleton_id,
        audit.binding_id,
        audit.context_id,
        model.model_id,
        audit.audit_id,
        audit.missing_support,
        3 - audit.missing_support.remaining_horizon,
    )


class LMBSampleTerminalKind(str, Enum):
    ACTIVE = "ACTIVE"
    HORIZON_TERMINAL = "HORIZON_TERMINAL"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


@dataclass(frozen=True, slots=True)
class LMBSampleAtomV1:
    terminal_kind: LMBSampleTerminalKind
    next_state: LMBState
    normalized_reward: Fraction
    failure: bool

    def __post_init__(self) -> None:
        if (
            type(self.terminal_kind) is not LMBSampleTerminalKind
            or type(self.next_state) is not LMBState
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or type(self.failure) is not bool
            or self.failure
            != (self.terminal_kind is LMBSampleTerminalKind.FAILURE)
        ):
            raise CrossDomainLMBInvariantViolation(
                "counter-sample atom is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_sample_atom.v1",
            "schema_version": SCHEMA_VERSION,
            "terminal_kind": self.terminal_kind.value,
            "next_state": _state_doc(self.next_state),
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
        }

    @property
    def atom_id(self) -> str:
        return _content_id("sample_atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class LMBSampleCountV1:
    atom: LMBSampleAtomV1
    count: int

    def __post_init__(self) -> None:
        if (
            type(self.atom) is not LMBSampleAtomV1
            or type(self.count) is not int
            or self.count <= 0
        ):
            raise CrossDomainLMBInvariantViolation(
                "sample atom count is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_sample_count.v1",
            "schema_version": SCHEMA_VERSION,
            "atom": self.atom.to_document(),
            "count": self.count,
        }

    @property
    def sample_count_id(self) -> str:
        return _content_id("sample_count", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "sample_count_id": self.sample_count_id}


@dataclass(frozen=True, slots=True)
class LMBCounterSampleTraceV1:
    authorization_id: str
    support_id: str
    randomness_assumption_id: str
    counter_domain: str
    counter_start: int
    draw_count: int
    candidate_block_count: int
    rejected_block_count: int
    action_draw_counts: tuple[tuple[int, int], ...]
    sample_counts: tuple[LMBSampleCountV1, ...]
    raw_block_commitment: str
    rejection_sampling_exact_uniform: bool = True
    unconditional_iid_claimed: bool = False
    exact_ground_rows_enumerated: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.authorization_id, "trace authorization"),
            (self.support_id, "trace support"),
            (self.randomness_assumption_id, "trace randomness assumption"),
            (self.raw_block_commitment, "trace raw commitment"),
        ):
            _cid(value, field)
        if (
            self.randomness_assumption_id
            != lmb_randomness_assumption_v1().assumption_id
            or
            self.counter_domain
            != "acfqp:cross-domain-lmb-counter-draw:v1"
            or self.counter_start != 0
            or self.draw_count != SAMPLE_COUNT_PER_SUPPORT
            or type(self.candidate_block_count) is not int
            or type(self.rejected_block_count) is not int
            or self.rejected_block_count < 0
            or self.candidate_block_count
            != self.draw_count + self.rejected_block_count
            or type(self.action_draw_counts) is not tuple
            or not self.action_draw_counts
            or self.action_draw_counts
            != tuple(sorted(self.action_draw_counts))
            or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not int
                or type(item[1]) is not int
                or item[1] < 0
                for item in self.action_draw_counts
            )
            or sum(item[1] for item in self.action_draw_counts)
            != self.draw_count
            or type(self.sample_counts) is not tuple
            or not self.sample_counts
            or any(type(item) is not LMBSampleCountV1 for item in self.sample_counts)
            or tuple(item.atom.atom_id for item in self.sample_counts)
            != tuple(sorted({item.atom.atom_id for item in self.sample_counts}))
            or sum(item.count for item in self.sample_counts) != self.draw_count
            or self.rejection_sampling_exact_uniform is not True
            or self.unconditional_iid_claimed is not False
            or self.exact_ground_rows_enumerated != 0
        ):
            raise CrossDomainLMBInvariantViolation(
                "counter sample trace is incomplete or enumerated exact rows"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_counter_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "authorization_id": self.authorization_id,
            "support_id": self.support_id,
            "randomness_assumption_id": self.randomness_assumption_id,
            "counter_domain": self.counter_domain,
            "counter_start": self.counter_start,
            "draw_count": self.draw_count,
            "candidate_block_count": self.candidate_block_count,
            "rejected_block_count": self.rejected_block_count,
            "action_draw_counts": [list(item) for item in self.action_draw_counts],
            "sample_counts": [item.to_document() for item in self.sample_counts],
            "raw_block_commitment": self.raw_block_commitment,
            "rejection_sampling_exact_uniform": (
                self.rejection_sampling_exact_uniform
            ),
            "unconditional_iid_claimed": self.unconditional_iid_claimed,
            "exact_ground_rows_enumerated": (
                self.exact_ground_rows_enumerated
            ),
        }

    @property
    def trace_id(self) -> str:
        return _content_id("trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


def _counter_uniform(
    authorization_id: str,
    counter: int,
) -> tuple[int, bytes]:
    if type(counter) is not int or counter < 0:
        raise CrossDomainLMBInvariantViolation(
            "counter draw index must be nonnegative"
        )
    raw = hashlib.sha256(
        b"acfqp:cross-domain-lmb-counter-draw:v1\x00"
        + authorization_id.encode("ascii")
        + counter.to_bytes(8, "big")
    ).digest()
    return int.from_bytes(raw, "big"), raw


def _exact_uniform_ordinal(
    uniform_block: int,
    action_count: int,
) -> int | None:
    """Map one ideal 256-bit block to an exact uniform ordinal or reject it."""

    modulus = 1 << 256
    if (
        type(uniform_block) is not int
        or not 0 <= uniform_block < modulus
        or type(action_count) is not int
        or action_count <= 0
        or action_count > modulus
    ):
        raise CrossDomainLMBInvariantViolation(
            "rejection-sampling input is outside its registered domain"
        )
    acceptance_limit = modulus - modulus % action_count
    return (
        None
        if uniform_block >= acceptance_limit
        else uniform_block % action_count
    )


def _sample_atom(
    context: LMBTargetContextV1,
    support: LMBSemanticSupportV1,
    action: LMBAction,
) -> LMBSampleAtomV1:
    outcome = context.kernel().step(support.state, action)[0]
    reward = Fraction(dict(outcome.reward_features).get("match", 0))
    if outcome.failure:
        kind = LMBSampleTerminalKind.FAILURE
    elif outcome.next_state.status is LMBStatus.SUCCESS:
        kind = LMBSampleTerminalKind.SUCCESS
    elif support.remaining_horizon == 1:
        kind = LMBSampleTerminalKind.HORIZON_TERMINAL
    else:
        kind = LMBSampleTerminalKind.ACTIVE
    return LMBSampleAtomV1(
        kind,
        outcome.next_state,
        reward,
        outcome.failure,
    )


def acquire_lmb_support_trace_v1(
    context: LMBTargetContextV1,
    authorization: LMBSupportAuthorizationV1,
) -> LMBCounterSampleTraceV1:
    """Acquire only one authorized semantic support.

    Candidate SHA-256 blocks are rejection-sampled below the largest multiple
    of the action count.  Thus the concretizer is exactly uniform conditional
    on the registered random-oracle assumption, including when the action
    count does not divide ``2**256``.
    """

    if (
        type(context) is not LMBTargetContextV1
        or type(authorization) is not LMBSupportAuthorizationV1
        or authorization.context_id != context.context_id
        or authorization.support.context_id != context.context_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "target support acquisition identity mismatch"
        )
    support = authorization.support
    kernel = context.kernel()
    legal = kernel.actions(support.state)
    actions = tuple(LMBAction(tile) for tile in support.ground_action_tiles)
    if any(item not in legal for item in actions):
        raise CrossDomainLMBInvariantViolation(
            "authorized concretizer contains an illegal action"
        )
    atom_counts: dict[LMBSampleAtomV1, int] = {}
    action_counts = {item.tile: 0 for item in actions}
    commitment = hashlib.sha256(
        b"acfqp:cross-domain-lmb-raw-draw-commitment:v1\x00"
    )
    accepted_draws = 0
    candidate_blocks = 0
    rejected_blocks = 0
    while accepted_draws < authorization.draw_count:
        uniform, raw = _counter_uniform(
            authorization.authorization_id,
            candidate_blocks,
        )
        ordinal = _exact_uniform_ordinal(uniform, len(actions))
        commitment.update(candidate_blocks.to_bytes(8, "big"))
        commitment.update(raw)
        candidate_blocks += 1
        if ordinal is None:
            rejected_blocks += 1
            commitment.update(b"REJECT")
            continue
        action = actions[ordinal]
        atom = _sample_atom(context, support, action)
        action_counts[action.tile] += 1
        atom_counts[atom] = atom_counts.get(atom, 0) + 1
        commitment.update(b"ACCEPT")
        commitment.update(accepted_draws.to_bytes(8, "big"))
        commitment.update(action.tile.to_bytes(2, "big"))
        commitment.update(atom.atom_id.encode("ascii"))
        accepted_draws += 1
    counts = tuple(
        LMBSampleCountV1(atom, count)
        for atom, count in sorted(
            atom_counts.items(),
            key=lambda item: item[0].atom_id,
        )
    )
    return LMBCounterSampleTraceV1(
        authorization.authorization_id,
        support.support_id,
        lmb_randomness_assumption_v1().assumption_id,
        "acfqp:cross-domain-lmb-counter-draw:v1",
        0,
        authorization.draw_count,
        candidate_blocks,
        rejected_blocks,
        tuple(sorted(action_counts.items())),
        counts,
        commitment.hexdigest(),
    )


@dataclass(frozen=True, slots=True)
class LMBEvidenceVerificationV1:
    context_id: str
    authorization_id: str
    trace_id: str
    raw_counter_draws_replayed: int
    candidate_counter_blocks_replayed: int
    rejected_counter_blocks_replayed: int
    exact_trace_match: bool
    support_and_epoch_match: bool
    fixed_concretizer_replayed: bool
    conditional_random_oracle_assumption_checked: bool = True
    unconditional_iid_claimed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "verification context"),
            (self.authorization_id, "verification authorization"),
            (self.trace_id, "verification trace"),
        ):
            _cid(value, field)
        if (
            self.raw_counter_draws_replayed != SAMPLE_COUNT_PER_SUPPORT
            or self.candidate_counter_blocks_replayed
            != (
                self.raw_counter_draws_replayed
                + self.rejected_counter_blocks_replayed
            )
            or self.rejected_counter_blocks_replayed < 0
            or self.exact_trace_match is not True
            or self.support_and_epoch_match is not True
            or self.fixed_concretizer_replayed is not True
            or self.conditional_random_oracle_assumption_checked is not True
            or self.unconditional_iid_claimed is not False
        ):
            raise CrossDomainLMBInvariantViolation(
                "LMB evidence verification is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_evidence_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "authorization_id": self.authorization_id,
            "trace_id": self.trace_id,
            "raw_counter_draws_replayed": self.raw_counter_draws_replayed,
            "candidate_counter_blocks_replayed": (
                self.candidate_counter_blocks_replayed
            ),
            "rejected_counter_blocks_replayed": (
                self.rejected_counter_blocks_replayed
            ),
            "exact_trace_match": self.exact_trace_match,
            "support_and_epoch_match": self.support_and_epoch_match,
            "fixed_concretizer_replayed": (
                self.fixed_concretizer_replayed
            ),
            "conditional_random_oracle_assumption_checked": (
                self.conditional_random_oracle_assumption_checked
            ),
            "unconditional_iid_claimed": self.unconditional_iid_claimed,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("evidence_verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_lmb_support_trace_v1(
    context: LMBTargetContextV1,
    authorization: LMBSupportAuthorizationV1,
    claimed: LMBCounterSampleTraceV1,
) -> LMBEvidenceVerificationV1:
    if (
        type(context) is not LMBTargetContextV1
        or type(authorization) is not LMBSupportAuthorizationV1
        or type(claimed) is not LMBCounterSampleTraceV1
        or authorization.context_id != context.context_id
        or claimed.authorization_id != authorization.authorization_id
        or claimed.support_id != authorization.support.support_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "sample-trace verification identity mismatch"
        )
    expected = acquire_lmb_support_trace_v1(context, authorization)
    _runtime_shape(claimed, expected, "LMB counter trace")
    if claimed.to_document() != expected.to_document():
        raise CrossDomainLMBInvariantViolation(
            "raw counter trace or aggregate counts were altered"
        )
    return LMBEvidenceVerificationV1(
        context.context_id,
        authorization.authorization_id,
        claimed.trace_id,
        claimed.draw_count,
        claimed.candidate_block_count,
        claimed.rejected_block_count,
        True,
        True,
        True,
    )


def _interval(empirical: Fraction) -> tuple[Fraction, Fraction]:
    return (
        max(Fraction(0), empirical - HOEFFDING_RADIUS),
        min(Fraction(1), empirical + HOEFFDING_RADIUS),
    )


def model_row_from_verified_trace_v1(
    authorization: LMBSupportAuthorizationV1,
    trace: LMBCounterSampleTraceV1,
    verification: LMBEvidenceVerificationV1,
) -> LMBStatisticalModelRowV1:
    if (
        type(authorization) is not LMBSupportAuthorizationV1
        or type(trace) is not LMBCounterSampleTraceV1
        or type(verification) is not LMBEvidenceVerificationV1
        or trace.authorization_id != authorization.authorization_id
        or verification.authorization_id != authorization.authorization_id
        or verification.trace_id != trace.trace_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "only verified support evidence may enter a target model"
        )
    total = Fraction(trace.draw_count)
    reward = sum(
        (
            Fraction(item.count) * item.atom.normalized_reward
            for item in trace.sample_counts
        ),
        Fraction(0),
    ) / total
    failure = sum(
        Fraction(item.count)
        for item in trace.sample_counts
        if item.atom.failure
    ) / total
    active = sum(
        Fraction(item.count)
        for item in trace.sample_counts
        if item.atom.terminal_kind is LMBSampleTerminalKind.ACTIVE
    ) / total
    horizon = sum(
        Fraction(item.count)
        for item in trace.sample_counts
        if item.atom.terminal_kind
        is LMBSampleTerminalKind.HORIZON_TERMINAL
    ) / total
    reward_interval = _interval(reward)
    failure_interval = _interval(failure)
    active_interval = _interval(active)
    horizon_interval = _interval(horizon)
    active_states = {
        item.atom.next_state
        for item in trace.sample_counts
        if item.atom.terminal_kind is LMBSampleTerminalKind.ACTIVE
    }
    if len(active_states) > 1:
        raise CrossDomainLMBInvariantViolation(
            "registered root support revealed multiple concrete continuations"
        )
    return LMBStatisticalModelRowV1(
        authorization.support,
        trace.trace_id,
        reward,
        failure,
        active,
        horizon,
        *reward_interval,
        *failure_interval,
        *active_interval,
        *horizon_interval,
        next(iter(active_states)) if active_states else None,
    )


def overlay_lmb_statistical_row_v1(
    model: LMBPartialStatisticalRAPMV1,
    row: LMBStatisticalModelRowV1,
) -> LMBPartialStatisticalRAPMV1:
    if (
        type(model) is not LMBPartialStatisticalRAPMV1
        or type(row) is not LMBStatisticalModelRowV1
        or row.support.skeleton_id != model.skeleton_id
        or row.support.binding_id != model.binding_id
        or row.support.context_id != model.context_id
        or model.epoch_index >= 2
        or any(
            item.support.remaining_horizon
            == row.support.remaining_horizon
            for item in model.rows
        )
        or row.support.remaining_horizon != 2 - model.epoch_index
    ):
        raise CrossDomainLMBInvariantViolation(
            "statistical overlay is stale, duplicate, or out of order"
        )
    rows = tuple(sorted((*model.rows, row), key=lambda item: item.row_id))
    return LMBPartialStatisticalRAPMV1(
        model.skeleton_id,
        model.binding_id,
        model.context_id,
        model.epoch_index + 1,
        model.model_id,
        rows,
    )


@dataclass(frozen=True, slots=True)
class CrossDomainLMBCalibrationV1:
    sample_count_per_support: int = SAMPLE_COUNT_PER_SUPPORT
    radius: Fraction = HOEFFDING_RADIUS
    exponent: Fraction = Fraction(2048, 225)
    taylor_degree: int = 19
    taylor_lower: Fraction = Fraction(0)
    per_atom_tail_upper: Fraction = PER_ATOM_TAIL_UPPER
    preregistered_atom_obligations: int = (
        PREREGISTERED_ATOM_OBLIGATIONS
    )
    family_tail_upper: Fraction = FAMILY_TAIL_UPPER
    family_confidence_lower: Fraction = FAMILY_CONFIDENCE_LOWER
    randomness_assumption_id: str = (
        lmb_randomness_assumption_v1().assumption_id
    )
    confidence_semantics: str = (
        "conditional_on_registered_random_oracle_and_iid_simulator_assumption"
    )
    unconditional_iid_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.randomness_assumption_id, "calibration randomness assumption")
        expected_taylor = sum(
            self.exponent**degree / math.factorial(degree)
            for degree in range(self.taylor_degree + 1)
        )
        if (
            self.sample_count_per_support != 16_384
            or self.radius != Fraction(1, 60)
            or self.exponent
            != 2 * self.sample_count_per_support * self.radius**2
            or self.taylor_degree != 19
            or self.taylor_lower != expected_taylor
            or self.taylor_lower <= 8_000
            or self.per_atom_tail_upper != Fraction(1, 4_000)
            or Fraction(2, 1) / self.taylor_lower
            > self.per_atom_tail_upper
            or self.preregistered_atom_obligations != 64
            or self.family_tail_upper != Fraction(2, 125)
            or self.family_confidence_lower != Fraction(123, 125)
            or self.family_confidence_lower <= Fraction(19, 20)
            or self.randomness_assumption_id
            != lmb_randomness_assumption_v1().assumption_id
            or self.confidence_semantics
            != (
                "conditional_on_registered_random_oracle_and_iid_"
                "simulator_assumption"
            )
            or self.unconditional_iid_claimed is not False
        ):
            raise CrossDomainLMBInvariantViolation(
                "cross-domain LMB Hoeffding calibration changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_calibration.v1",
            "schema_version": SCHEMA_VERSION,
            "sample_count_per_support": self.sample_count_per_support,
            "radius": _fdoc(self.radius),
            "exponent": _fdoc(self.exponent),
            "taylor_degree": self.taylor_degree,
            "taylor_lower": _fdoc(self.taylor_lower),
            "per_atom_tail_upper": _fdoc(self.per_atom_tail_upper),
            "preregistered_atom_obligations": (
                self.preregistered_atom_obligations
            ),
            "family_tail_upper": _fdoc(self.family_tail_upper),
            "family_confidence_lower": _fdoc(
                self.family_confidence_lower
            ),
            "randomness_assumption_id": self.randomness_assumption_id,
            "confidence_semantics": self.confidence_semantics,
            "unconditional_iid_claimed": self.unconditional_iid_claimed,
        }

    @property
    def calibration_id(self) -> str:
        return _content_id("calibration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "calibration_id": self.calibration_id}


def cross_domain_lmb_calibration_v1() -> CrossDomainLMBCalibrationV1:
    exponent = Fraction(2048, 225)
    lower = sum(
        exponent**degree / math.factorial(degree)
        for degree in range(20)
    )
    return CrossDomainLMBCalibrationV1(taylor_lower=lower)


@dataclass(frozen=True, slots=True)
class LMBQueryV1:
    context_id: str
    occurrence_key: str
    root_state: LMBState
    horizon: int = HORIZON
    risk_tolerance: Fraction = RISK_TOLERANCE
    regret_tolerance: Fraction = REGRET_TOLERANCE
    reward_normalizer: Fraction = REWARD_NORMALIZER

    def __post_init__(self) -> None:
        _cid(self.context_id, "query context")
        if (
            type(self.occurrence_key) is not str
            or not self.occurrence_key
            or type(self.root_state) is not LMBState
            or self.horizon != 2
            or self.risk_tolerance != Fraction(1, 20)
            or self.regret_tolerance != Fraction(1, 20)
            or self.reward_normalizer != 2
        ):
            raise CrossDomainLMBInvariantViolation(
                "registered LMB query changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_query.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "occurrence_key": self.occurrence_key,
            "root_state": _state_doc(self.root_state),
            "horizon": self.horizon,
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "regret_tolerance": _fdoc(self.regret_tolerance),
            "reward_weights": {"match": 1, "terminal_clear": 0},
            "reward_normalizer": _fdoc(self.reward_normalizer),
            "normalizer_proof": "match_count_le_horizon_v1",
        }

    @property
    def query_id(self) -> str:
        return _content_id("query", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}


@dataclass(frozen=True, slots=True)
class LMBOccurrenceCertificateV1:
    query: LMBQueryV1
    model_id: str
    source_audit_id: str
    selected_root_action_coordinate: int
    selected_continuation_action_coordinate: int
    reward_lower: Fraction
    failure_upper: Fraction
    normalized_regret_upper: Fraction
    new_target_draws: int = 0

    def __post_init__(self) -> None:
        if type(self.query) is not LMBQueryV1:
            raise CrossDomainLMBInvariantViolation(
                "occurrence query runtime type changed"
            )
        _cid(self.model_id, "occurrence model")
        _cid(self.source_audit_id, "occurrence source audit")
        if (
            self.selected_root_action_coordinate != 2
            or self.selected_continuation_action_coordinate != 1
            or self.reward_lower != Fraction(59, 60)
            or self.failure_upper != Fraction(119, 3600)
            or self.normalized_regret_upper != Fraction(1, 60)
            or self.new_target_draws != 0
        ):
            raise CrossDomainLMBInvariantViolation(
                "reused occurrence certificate or bounds changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "query": self.query.to_document(),
            "model_id": self.model_id,
            "source_audit_id": self.source_audit_id,
            "selected_root_action_coordinate": (
                self.selected_root_action_coordinate
            ),
            "selected_continuation_action_coordinate": (
                self.selected_continuation_action_coordinate
            ),
            "reward_lower": _fdoc(self.reward_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "new_target_draws": self.new_target_draws,
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


@dataclass(frozen=True, slots=True)
class LMBColdDirectControlV1:
    context_id: str
    query_ids: tuple[str, ...]
    complete_h2_ground_row_count: int
    exact_optimal_reward: Fraction
    exact_optimal_failure: Fraction
    selected_root_tile: int
    portable_skeleton_used: bool = False
    reusable_model_used: bool = False
    lane: str = "standalone_evaluation_only"

    def __post_init__(self) -> None:
        _cid(self.context_id, "cold context")
        if (
            type(self.query_ids) is not tuple
            or len(self.query_ids) != 2
            or self.query_ids != tuple(sorted(set(self.query_ids)))
            or any(
                parse_content_id(item) != item for item in self.query_ids
            )
            or self.complete_h2_ground_row_count not in (3, 5)
            or self.exact_optimal_reward != 1
            or self.exact_optimal_failure != 0
            or type(self.selected_root_tile) is not int
            or self.portable_skeleton_used is not False
            or self.reusable_model_used is not False
            or self.lane != "standalone_evaluation_only"
        ):
            raise CrossDomainLMBInvariantViolation(
                "cold direct LMB control changed lanes or exact result"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_cold_control.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "query_ids": list(self.query_ids),
            "complete_h2_ground_row_count": (
                self.complete_h2_ground_row_count
            ),
            "exact_optimal_reward": _fdoc(self.exact_optimal_reward),
            "exact_optimal_failure": _fdoc(self.exact_optimal_failure),
            "selected_root_tile": self.selected_root_tile,
            "portable_skeleton_used": self.portable_skeleton_used,
            "reusable_model_used": self.reusable_model_used,
            "lane": self.lane,
        }

    @property
    def control_id(self) -> str:
        return _content_id("cold", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def cold_exact_lmb_h2_control_v1(
    context: LMBTargetContextV1,
    queries: tuple[LMBQueryV1, ...],
) -> LMBColdDirectControlV1:
    if (
        type(context) is not LMBTargetContextV1
        or type(queries) is not tuple
        or len(queries) != 2
        or any(
            type(item) is not LMBQueryV1
            or item.context_id != context.context_id
            for item in queries
        )
    ):
        raise CrossDomainLMBInvariantViolation(
            "cold exact comparator query scope changed"
        )
    kernel = context.kernel()
    root = context.root_state
    root_actions = kernel.actions(root)
    closure_rows = len(root_actions)
    best: tuple[Fraction, Fraction, int] | None = None
    for action in root_actions:
        first = kernel.step(root, action)[0]
        reward = Fraction(dict(first.reward_features).get("match", 0))
        failure = Fraction(int(first.failure))
        if not first.terminal:
            continuation_actions = kernel.actions(first.next_state)
            closure_rows += len(continuation_actions)
            continuation_best = Fraction(0)
            continuation_failure = Fraction(1)
            for continuation in continuation_actions:
                second = kernel.step(first.next_state, continuation)[0]
                second_reward = Fraction(
                    dict(second.reward_features).get("match", 0)
                )
                second_failure = Fraction(int(second.failure))
                candidate = (second_reward, -second_failure)
                prior = (continuation_best, -continuation_failure)
                if candidate > prior:
                    continuation_best = second_reward
                    continuation_failure = second_failure
            reward += continuation_best
            failure = max(failure, continuation_failure)
        candidate_row = (reward, -failure, -action.tile)
        if best is None or candidate_row > (
            best[0],
            -best[1],
            -best[2],
        ):
            best = (reward, failure, action.tile)
    if (
        best is None
        or best
        != (
            Fraction(1),
            Fraction(0),
            context.selected_root_tile,
        )
    ):
        raise CrossDomainLMBInvariantViolation(
            "cold exact H2 optimum changed"
        )
    return LMBColdDirectControlV1(
        context.context_id,
        tuple(sorted(item.query_id for item in queries)),
        closure_rows,
        best[0],
        best[1],
        best[2],
    )


@dataclass(frozen=True, slots=True)
class LMBTargetContextResultV1:
    context: LMBTargetContextV1
    binding_id: str
    initial_model: LMBPartialStatisticalRAPMV1
    first_audit: LMBSoundAuditV1
    first_authorization: LMBSupportAuthorizationV1
    first_trace: LMBCounterSampleTraceV1
    first_verification: LMBEvidenceVerificationV1
    intermediate_model: LMBPartialStatisticalRAPMV1
    second_audit: LMBSoundAuditV1
    second_authorization: LMBSupportAuthorizationV1
    second_trace: LMBCounterSampleTraceV1
    second_verification: LMBEvidenceVerificationV1
    final_model: LMBPartialStatisticalRAPMV1
    final_audit: LMBSoundAuditV1
    occurrences: tuple[LMBOccurrenceCertificateV1, ...]
    operational_support_count: int = 2
    operational_draw_count: int = 2 * SAMPLE_COUNT_PER_SUPPORT
    exact_target_transition_rows_operational: int = 0

    def __post_init__(self) -> None:
        if type(self.context) is not LMBTargetContextV1:
            raise CrossDomainLMBInvariantViolation(
                "context result context runtime type changed"
            )
        _cid(self.binding_id, "context result binding")
        typed = (
            (self.initial_model, LMBPartialStatisticalRAPMV1),
            (self.first_audit, LMBSoundAuditV1),
            (self.first_authorization, LMBSupportAuthorizationV1),
            (self.first_trace, LMBCounterSampleTraceV1),
            (self.first_verification, LMBEvidenceVerificationV1),
            (self.intermediate_model, LMBPartialStatisticalRAPMV1),
            (self.second_audit, LMBSoundAuditV1),
            (self.second_authorization, LMBSupportAuthorizationV1),
            (self.second_trace, LMBCounterSampleTraceV1),
            (self.second_verification, LMBEvidenceVerificationV1),
            (self.final_model, LMBPartialStatisticalRAPMV1),
            (self.final_audit, LMBSoundAuditV1),
        )
        if any(type(value) is not expected for value, expected in typed):
            raise CrossDomainLMBInvariantViolation(
                "context result nested runtime type changed"
            )
        if (
            self.initial_model.epoch_index != 0
            or self.intermediate_model.epoch_index != 1
            or self.final_model.epoch_index != 2
            or self.intermediate_model.parent_model_id
            != self.initial_model.model_id
            or self.final_model.parent_model_id
            != self.intermediate_model.model_id
            or self.first_audit.outcome
            is not LMBAuditOutcome.FAILED_MISSING_ROOT_SUPPORT
            or self.second_audit.outcome
            is not LMBAuditOutcome.FAILED_MISSING_CONTINUATION_SUPPORT
            or self.final_audit.outcome is not LMBAuditOutcome.CERTIFIED
            or self.first_authorization.transaction_index != 1
            or self.second_authorization.transaction_index != 2
            or self.first_authorization.support.action_coordinate != 2
            or self.second_authorization.support.action_coordinate != 1
            or self.final_audit.reward_lower != Fraction(59, 60)
            or self.final_audit.reward_upper != Fraction(61, 60)
            or self.final_audit.unrestricted_reward_upper
            != Fraction(61, 60)
            or self.final_audit.failure_upper != Fraction(119, 3600)
            or self.final_audit.normalized_regret_upper != Fraction(1, 60)
            or type(self.occurrences) is not tuple
            or len(self.occurrences) != 2
            or any(
                type(item) is not LMBOccurrenceCertificateV1
                or item.model_id != self.final_model.model_id
                or item.source_audit_id != self.final_audit.audit_id
                for item in self.occurrences
            )
            or len({item.query.query_id for item in self.occurrences}) != 2
            or self.operational_support_count != 2
            or self.operational_draw_count != 32_768
            or self.exact_target_transition_rows_operational != 0
        ):
            raise CrossDomainLMBInvariantViolation(
                "context result chronology, golden bounds, or reuse changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_context_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "binding_id": self.binding_id,
            "initial_model": self.initial_model.to_document(),
            "first_audit": self.first_audit.to_document(),
            "first_authorization": self.first_authorization.to_document(),
            "first_trace": self.first_trace.to_document(),
            "first_verification": self.first_verification.to_document(),
            "intermediate_model": self.intermediate_model.to_document(),
            "second_audit": self.second_audit.to_document(),
            "second_authorization": self.second_authorization.to_document(),
            "second_trace": self.second_trace.to_document(),
            "second_verification": self.second_verification.to_document(),
            "final_model": self.final_model.to_document(),
            "final_audit": self.final_audit.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "operational_support_count": self.operational_support_count,
            "operational_draw_count": self.operational_draw_count,
            "exact_target_transition_rows_operational": (
                self.exact_target_transition_rows_operational
            ),
        }

    @property
    def result_id(self) -> str:
        return _content_id("context_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "result_id": self.result_id}


def run_lmb_target_context_v1(
    skeleton: Any,
    binding: LMBSlotBindingV1,
    context: LMBTargetContextV1,
) -> LMBTargetContextResultV1:
    skeleton_id, *_ = _portable_shape(skeleton)
    if (
        type(binding) is not LMBSlotBindingV1
        or type(context) is not LMBTargetContextV1
        or binding.skeleton_id != skeleton_id
        or binding.semantics_id != context.semantics_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "target context runner identity mismatch"
        )
    initial = initial_lmb_partial_statistical_rapm_v1(binding, context)
    first_audit = audit_lmb_partial_statistical_rapm_v1(
        skeleton,
        binding,
        context,
        initial,
    )
    first_authorization = authorize_missing_lmb_support_v1(
        first_audit,
        initial,
    )
    first_trace = acquire_lmb_support_trace_v1(
        context,
        first_authorization,
    )
    first_verification = verify_lmb_support_trace_v1(
        context,
        first_authorization,
        first_trace,
    )
    first_row = model_row_from_verified_trace_v1(
        first_authorization,
        first_trace,
        first_verification,
    )
    intermediate = overlay_lmb_statistical_row_v1(initial, first_row)
    second_audit = audit_lmb_partial_statistical_rapm_v1(
        skeleton,
        binding,
        context,
        intermediate,
    )
    second_authorization = authorize_missing_lmb_support_v1(
        second_audit,
        intermediate,
    )
    second_trace = acquire_lmb_support_trace_v1(
        context,
        second_authorization,
    )
    second_verification = verify_lmb_support_trace_v1(
        context,
        second_authorization,
        second_trace,
    )
    second_row = model_row_from_verified_trace_v1(
        second_authorization,
        second_trace,
        second_verification,
    )
    final_model = overlay_lmb_statistical_row_v1(
        intermediate,
        second_row,
    )
    final_audit = audit_lmb_partial_statistical_rapm_v1(
        skeleton,
        binding,
        context,
        final_model,
    )
    queries = tuple(
        LMBQueryV1(
            context.context_id,
            f"{context.context_key}:occurrence:{ordinal}",
            context.root_state,
        )
        for ordinal in (1, 2)
    )
    occurrences = tuple(
        LMBOccurrenceCertificateV1(
            query,
            final_model.model_id,
            final_audit.audit_id,
            final_audit.selected_root_action_coordinate,
            (
                final_audit.selected_continuation_action_coordinate
                if final_audit.selected_continuation_action_coordinate
                is not None
                else -1
            ),
            final_audit.reward_lower,
            final_audit.failure_upper,
            final_audit.normalized_regret_upper,
        )
        for query in queries
    )
    return LMBTargetContextResultV1(
        context,
        binding.binding_id,
        initial,
        first_audit,
        first_authorization,
        first_trace,
        first_verification,
        intermediate,
        second_audit,
        second_authorization,
        second_trace,
        second_verification,
        final_model,
        final_audit,
        occurrences,
    )


@dataclass(frozen=True, slots=True)
class LMBNoTransferControlV1:
    context_id: str
    abstract_model_built: bool
    abstract_certificate_count: int
    direct_fallback_control_id: str
    direct_reward: Fraction
    direct_failure: Fraction
    target_program_search_performed: bool = False
    standalone_direct_control_consumed: bool = True

    def __post_init__(self) -> None:
        _cid(self.context_id, "no-transfer context")
        _cid(self.direct_fallback_control_id, "no-transfer fallback")
        if (
            self.abstract_model_built is not False
            or self.abstract_certificate_count != 0
            or self.direct_reward != 1
            or self.direct_failure != 0
            or self.target_program_search_performed is not False
            or self.standalone_direct_control_consumed is not True
        ):
            raise CrossDomainLMBInvariantViolation(
                "no-transfer control minted an abstract claim"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_no_transfer.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "abstract_model_built": self.abstract_model_built,
            "abstract_certificate_count": self.abstract_certificate_count,
            "direct_fallback_control_id": self.direct_fallback_control_id,
            "direct_reward": _fdoc(self.direct_reward),
            "direct_failure": _fdoc(self.direct_failure),
            "target_program_search_performed": (
                self.target_program_search_performed
            ),
            "standalone_direct_control_consumed": (
                self.standalone_direct_control_consumed
            ),
        }

    @property
    def control_id(self) -> str:
        return _content_id("no_transfer", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def run_lmb_no_transfer_control_v1(
    context: LMBTargetContextV1,
    cold_control: LMBColdDirectControlV1,
) -> LMBNoTransferControlV1:
    if (
        type(context) is not LMBTargetContextV1
        or type(cold_control) is not LMBColdDirectControlV1
        or cold_control.context_id != context.context_id
        or cold_control.lane != "standalone_evaluation_only"
    ):
        raise CrossDomainLMBInvariantViolation(
            "no-transfer control requires its matched standalone direct run"
        )
    return LMBNoTransferControlV1(
        context.context_id,
        False,
        0,
        cold_control.control_id,
        cold_control.exact_optimal_reward,
        cold_control.exact_optimal_failure,
    )


@dataclass(frozen=True, slots=True)
class LMBWrongBindingControlV1:
    bridge_log_id: str
    wrong_binding_key: str
    observed_alias_conflict_count: int
    no_sound_abstract_action: bool
    abstract_certificate_count: int
    bridge_alias_analysis_replayed: bool = True

    def __post_init__(self) -> None:
        _cid(self.bridge_log_id, "wrong-binding bridge")
        if (
            self.wrong_binding_key != "all_buffer_tokens"
            or self.observed_alias_conflict_count <= 0
            or self.no_sound_abstract_action is not True
            or self.abstract_certificate_count != 0
            or self.bridge_alias_analysis_replayed is not True
        ):
            raise CrossDomainLMBInvariantViolation(
                "wrong relation binding did not fail closed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_wrong_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "bridge_log_id": self.bridge_log_id,
            "wrong_binding_key": self.wrong_binding_key,
            "observed_alias_conflict_count": (
                self.observed_alias_conflict_count
            ),
            "no_sound_abstract_action": self.no_sound_abstract_action,
            "abstract_certificate_count": self.abstract_certificate_count,
            "bridge_alias_analysis_replayed": (
                self.bridge_alias_analysis_replayed
            ),
        }

    @property
    def control_id(self) -> str:
        return _content_id("wrong_binding", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def run_lmb_wrong_binding_control_v1(
    bridge_log: LMBBridgeLogV1,
    binding: LMBSlotBindingV1,
) -> LMBWrongBindingControlV1:
    if (
        type(bridge_log) is not LMBBridgeLogV1
        or type(binding) is not LMBSlotBindingV1
        or binding.bridge_log_id != bridge_log.bridge_log_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "wrong-binding control identity mismatch"
        )
    wrong_key = "all_buffer_tokens"
    signatures: dict[tuple[int, int], set[tuple[Any, ...]]] = {}
    for row in bridge_log.rows:
        signatures.setdefault(
            (row.state_action_count, row.binding_value(wrong_key)),
            set(),
        ).add(row.outcome_signature)
    conflict_count = sum(
        len(values) - 1
        for values in signatures.values()
        if len(values) > 1
    )
    registered = next(
        item for item in binding.candidates if item.binding_key == wrong_key
    )
    if conflict_count != registered.observed_alias_conflict_count:
        raise CrossDomainLMBInvariantViolation(
            "wrong-binding bridge replay differs from binding evidence"
        )
    return LMBWrongBindingControlV1(
        bridge_log.bridge_log_id,
        wrong_key,
        conflict_count,
        conflict_count > 0,
        0,
    )


@dataclass(frozen=True, slots=True)
class LMBSemanticOODControlV1:
    base_semantics_id: str
    ood_mechanism: str
    ood_semantics_id: str
    rejected_before_model: bool
    ground_draws_before_rejection: int
    abstract_certificate_count: int
    direct_fallback_required: bool
    control_scope: str = "semantic_registry_identity_mismatch_only"
    alternate_mechanism_executed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.base_semantics_id, "OOD base semantics"),
            (self.ood_semantics_id, "OOD mechanism semantics"),
        ):
            _cid(value, field)
        if (
            self.base_semantics_id == self.ood_semantics_id
            or self.ood_mechanism
            not in (
                "hidden_selected_tile_failure_v1",
                "match_arity_four_v1",
            )
            or self.rejected_before_model is not True
            or self.ground_draws_before_rejection != 0
            or self.abstract_certificate_count != 0
            or self.direct_fallback_required is not True
            or self.control_scope
            != "semantic_registry_identity_mismatch_only"
            or self.alternate_mechanism_executed is not False
        ):
            raise CrossDomainLMBInvariantViolation(
                "semantic OOD control did not reject before construction"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_ood.v1",
            "schema_version": SCHEMA_VERSION,
            "base_semantics_id": self.base_semantics_id,
            "ood_mechanism": self.ood_mechanism,
            "ood_semantics_id": self.ood_semantics_id,
            "rejected_before_model": self.rejected_before_model,
            "ground_draws_before_rejection": (
                self.ground_draws_before_rejection
            ),
            "abstract_certificate_count": self.abstract_certificate_count,
            "direct_fallback_required": self.direct_fallback_required,
            "control_scope": self.control_scope,
            "alternate_mechanism_executed": (
                self.alternate_mechanism_executed
            ),
        }

    @property
    def control_id(self) -> str:
        return _content_id("ood", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def run_lmb_semantic_ood_registry_control_v1(
    mechanism: str,
) -> LMBSemanticOODControlV1:
    if mechanism not in (
        "hidden_selected_tile_failure_v1",
        "match_arity_four_v1",
    ):
        raise CrossDomainLMBInvariantViolation(
            "unregistered LMB semantic OOD mechanism"
        )
    base_contract = {
        "match_arity": LMB_SEMANTICS.match_arity,
        "capacity": LMB_SEMANTICS.capacity,
        "failure_rule": "buffer_overflow_only",
    }
    alternate_contract = dict(base_contract)
    if mechanism == "hidden_selected_tile_failure_v1":
        alternate_contract["failure_rule"] = (
            "buffer_overflow_or_hidden_selected_tile"
        )
    else:
        alternate_contract["match_arity"] = 4
    rejected = alternate_contract != base_contract
    payload = {
        "schema": "acfqp.cross_domain_lmb_ood_semantics.v1",
        "base_semantics_id": LMB_SEMANTICS.semantics_id,
        "mechanism": mechanism,
        "alternate_contract": alternate_contract,
    }
    ood_id = hashlib.sha256(
        b"acfqp:cross-domain-lmb-ood-semantics:v1\x00"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return LMBSemanticOODControlV1(
        LMB_SEMANTICS.semantics_id,
        mechanism,
        ood_id,
        rejected,
        0,
        0,
        rejected,
    )


@dataclass(frozen=True, slots=True)
class LMBPermutationControlV1:
    source_context_id: str
    tile_permutation: tuple[int, ...]
    type_permutation: tuple[int, ...]
    root_support_multiset_preserved: bool
    continuation_support_multiset_preserved: bool
    selected_plan_mapped: bool
    reward_failure_preserved: bool

    def __post_init__(self) -> None:
        _cid(self.source_context_id, "permutation source context")
        if (
            self.tile_permutation != (5, 4, 3, 2, 1, 0)
            or self.type_permutation != (1, 0)
            or self.root_support_multiset_preserved is not True
            or self.continuation_support_multiset_preserved is not True
            or self.selected_plan_mapped is not True
            or self.reward_failure_preserved is not True
        ):
            raise CrossDomainLMBInvariantViolation(
                "tile/type relabeling changed relational semantics"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_permutation.v1",
            "schema_version": SCHEMA_VERSION,
            "source_context_id": self.source_context_id,
            "tile_permutation": list(self.tile_permutation),
            "type_permutation": list(self.type_permutation),
            "root_support_multiset_preserved": (
                self.root_support_multiset_preserved
            ),
            "continuation_support_multiset_preserved": (
                self.continuation_support_multiset_preserved
            ),
            "selected_plan_mapped": self.selected_plan_mapped,
            "reward_failure_preserved": self.reward_failure_preserved,
        }

    @property
    def control_id(self) -> str:
        return _content_id("permutation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


def lmb_tile_type_permutation_control_v1(
    context: LMBTargetContextV1,
    result: LMBTargetContextResultV1,
) -> LMBPermutationControlV1:
    if (
        type(context) is not LMBTargetContextV1
        or type(result) is not LMBTargetContextResultV1
        or result.context.context_id != context.context_id
    ):
        raise CrossDomainLMBInvariantViolation(
            "permutation control source mismatch"
        )
    mapping = (5, 4, 3, 2, 1, 0)
    type_mapping = (1, 0)
    kernel = context.kernel()

    def map_mask(mask: int) -> int:
        mapped = 0
        for old, new in enumerate(mapping):
            if mask & (1 << old):
                mapped |= 1 << new
        return mapped

    mapped_types = [0] * 6
    mapped_blockers: list[frozenset[int]] = [frozenset() for _ in range(6)]
    for old, new in enumerate(mapping):
        mapped_types[new] = type_mapping[kernel.tile_types[old]]
        mapped_blockers[new] = frozenset(
            mapping[item] for item in kernel.blockers[old]
        )
    mapped_kernel = LMBKernel(
        tuple(mapped_types),
        tuple(mapped_blockers),
        2,
        3,
        3,
    )
    mapped_root = LMBState(
        map_mask(context.root_state.removed_mask),
        tuple(reversed(context.root_state.buffer)),
    )
    original_root_supports = sorted(
        context.root_state.buffer[kernel.tile_types[item.tile]]
        for item in kernel.actions(context.root_state)
    )
    mapped_root_supports = sorted(
        mapped_root.buffer[mapped_kernel.tile_types[item.tile]]
        for item in mapped_kernel.actions(mapped_root)
    )
    original_selected = LMBAction(context.selected_root_tile)
    mapped_selected = LMBAction(mapping[context.selected_root_tile])
    original_first = kernel.step(context.root_state, original_selected)[0]
    mapped_first = mapped_kernel.step(mapped_root, mapped_selected)[0]
    original_cont_supports = sorted(
        original_first.next_state.buffer[kernel.tile_types[item.tile]]
        for item in kernel.actions(original_first.next_state)
    )
    mapped_cont_supports = sorted(
        mapped_first.next_state.buffer[mapped_kernel.tile_types[item.tile]]
        for item in mapped_kernel.actions(mapped_first.next_state)
    )
    return LMBPermutationControlV1(
        context.context_id,
        mapping,
        type_mapping,
        original_root_supports == mapped_root_supports,
        original_cont_supports == mapped_cont_supports,
        mapped_selected in mapped_kernel.actions(mapped_root),
        (
            dict(original_first.reward_features).get("match", 0)
            == dict(mapped_first.reward_features).get("match", 0)
            and original_first.failure == mapped_first.failure
        ),
    )


@dataclass(frozen=True, slots=True)
class LMBTransplantControlV1:
    cross_domain_row_rejected: bool
    cross_context_evidence_rejected: bool
    stale_epoch_authorization_rejected: bool
    altered_raw_trace_rejected: bool
    unregistered_semantics_rejected: bool

    def __post_init__(self) -> None:
        if not all(
            (
                self.cross_domain_row_rejected,
                self.cross_context_evidence_rejected,
                self.stale_epoch_authorization_rejected,
                self.altered_raw_trace_rejected,
                self.unregistered_semantics_rejected,
            )
        ):
            raise CrossDomainLMBInvariantViolation(
                "one identity/transplant attack was accepted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_transplant.v1",
            "schema_version": SCHEMA_VERSION,
            "cross_domain_row_rejected": self.cross_domain_row_rejected,
            "cross_context_evidence_rejected": (
                self.cross_context_evidence_rejected
            ),
            "stale_epoch_authorization_rejected": (
                self.stale_epoch_authorization_rejected
            ),
            "altered_raw_trace_rejected": (
                self.altered_raw_trace_rejected
            ),
            "unregistered_semantics_rejected": (
                self.unregistered_semantics_rejected
            ),
        }

    @property
    def control_id(self) -> str:
        return _content_id("transplant", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


@dataclass(frozen=True, slots=True)
class CrossDomainLMBCampaignV1:
    skeleton_id: str
    bridge_log: LMBBridgeLogV1
    binding: LMBSlotBindingV1
    calibration: CrossDomainLMBCalibrationV1
    target_results: tuple[LMBTargetContextResultV1, ...]
    cold_controls: tuple[LMBColdDirectControlV1, ...]
    no_transfer_controls: tuple[LMBNoTransferControlV1, ...]
    wrong_binding_control: LMBWrongBindingControlV1
    semantic_ood_controls: tuple[LMBSemanticOODControlV1, ...]
    permutation_control: LMBPermutationControlV1
    transplant_control: LMBTransplantControlV1
    status: str = SUCCESS_STATUS
    operational_support_count: int = POSITIVE_SUPPORT_COUNT
    operational_target_draw_count: int = POSITIVE_DRAW_COUNT
    operational_exact_ground_row_count: int = 0
    standalone_cold_ground_row_count: int = 13
    occurrence_count: int = 6
    source_graph_skeleton_reused: bool = True
    source_dynamics_imported: bool = False
    target_program_generation_count: int = 0
    automatic_slot_binding_within_frozen_adapter_claimed: bool = True
    bridge_supervision_scope: str = (
        "human_frozen_ontology_query_neutral_exact_bridge_v1"
    )
    automatic_ontology_alignment_claimed: bool = False
    sample_efficiency_claimed: bool = False
    randomness_assumption_id: str = (
        lmb_randomness_assumption_v1().assumption_id
    )
    statistical_confidence_conditional: bool = True
    unconditional_iid_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None

    def __post_init__(self) -> None:
        _cid(self.skeleton_id, "campaign skeleton")
        _cid(self.randomness_assumption_id, "campaign randomness assumption")
        typed = (
            (self.bridge_log, LMBBridgeLogV1),
            (self.binding, LMBSlotBindingV1),
            (self.calibration, CrossDomainLMBCalibrationV1),
            (self.wrong_binding_control, LMBWrongBindingControlV1),
            (self.permutation_control, LMBPermutationControlV1),
            (self.transplant_control, LMBTransplantControlV1),
        )
        if any(type(value) is not expected for value, expected in typed):
            raise CrossDomainLMBInvariantViolation(
                "campaign nested runtime type changed"
            )
        if (
            self.binding.skeleton_id != self.skeleton_id
            or self.binding.bridge_log_id != self.bridge_log.bridge_log_id
            or type(self.target_results) is not tuple
            or len(self.target_results) != 3
            or any(
                type(item) is not LMBTargetContextResultV1
                or item.binding_id != self.binding.binding_id
                for item in self.target_results
            )
            or tuple(item.context for item in self.target_results)
            != registered_lmb_target_contexts_v1()
            or type(self.cold_controls) is not tuple
            or len(self.cold_controls) != 3
            or any(
                type(item) is not LMBColdDirectControlV1
                for item in self.cold_controls
            )
            or tuple(item.context_id for item in self.cold_controls)
            != tuple(
                item.context.context_id for item in self.target_results
            )
            or type(self.no_transfer_controls) is not tuple
            or len(self.no_transfer_controls) != 3
            or any(
                type(item) is not LMBNoTransferControlV1
                for item in self.no_transfer_controls
            )
            or type(self.semantic_ood_controls) is not tuple
            or tuple(item.ood_mechanism for item in self.semantic_ood_controls)
            != (
                "hidden_selected_tile_failure_v1",
                "match_arity_four_v1",
            )
            or self.status != SUCCESS_STATUS
            or self.operational_support_count != 6
            or self.operational_target_draw_count != 98_304
            or self.operational_exact_ground_row_count != 0
            or self.standalone_cold_ground_row_count != 13
            or self.occurrence_count != 6
            or self.source_graph_skeleton_reused is not True
            or self.source_dynamics_imported is not False
            or self.target_program_generation_count != 0
            or self.automatic_slot_binding_within_frozen_adapter_claimed
            is not True
            or self.bridge_supervision_scope
            != "human_frozen_ontology_query_neutral_exact_bridge_v1"
            or self.automatic_ontology_alignment_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.randomness_assumption_id
            != lmb_randomness_assumption_v1().assumption_id
            or self.statistical_confidence_conditional is not True
            or self.unconditional_iid_claimed is not False
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
        ):
            raise CrossDomainLMBInvariantViolation(
                "campaign totals, transfer boundary, or locks changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "skeleton_id": self.skeleton_id,
            "bridge_log": self.bridge_log.to_document(),
            "binding": self.binding.to_document(),
            "calibration": self.calibration.to_document(),
            "target_results": [
                item.to_document() for item in self.target_results
            ],
            "cold_controls": [
                item.to_document() for item in self.cold_controls
            ],
            "no_transfer_controls": [
                item.to_document() for item in self.no_transfer_controls
            ],
            "wrong_binding_control": (
                self.wrong_binding_control.to_document()
            ),
            "semantic_ood_controls": [
                item.to_document() for item in self.semantic_ood_controls
            ],
            "permutation_control": self.permutation_control.to_document(),
            "transplant_control": self.transplant_control.to_document(),
            "status": self.status,
            "operational_support_count": self.operational_support_count,
            "operational_target_draw_count": (
                self.operational_target_draw_count
            ),
            "operational_exact_ground_row_count": (
                self.operational_exact_ground_row_count
            ),
            "standalone_cold_ground_row_count": (
                self.standalone_cold_ground_row_count
            ),
            "occurrence_count": self.occurrence_count,
            "source_graph_skeleton_reused": (
                self.source_graph_skeleton_reused
            ),
            "source_dynamics_imported": self.source_dynamics_imported,
            "target_program_generation_count": (
                self.target_program_generation_count
            ),
            "automatic_slot_binding_within_frozen_adapter_claimed": (
                self.automatic_slot_binding_within_frozen_adapter_claimed
            ),
            "bridge_supervision_scope": self.bridge_supervision_scope,
            "automatic_ontology_alignment_claimed": (
                self.automatic_ontology_alignment_claimed
            ),
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "randomness_assumption_id": self.randomness_assumption_id,
            "statistical_confidence_conditional": (
                self.statistical_confidence_conditional
            ),
            "unconditional_iid_claimed": self.unconditional_iid_claimed,
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
        }

    @property
    def campaign_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_id": self.campaign_id}


def _run_cross_domain_lmb_campaign_uncached_v1(
    skeleton: Any,
) -> CrossDomainLMBCampaignV1:
    skeleton_id, *_ = _portable_shape(skeleton)
    bridge = query_neutral_lmb_bridge_log_v1()
    binding = bind_lmb_relational_slot_v1(skeleton, bridge)
    calibration = cross_domain_lmb_calibration_v1()
    results = tuple(
        run_lmb_target_context_v1(skeleton, binding, context)
        for context in registered_lmb_target_contexts_v1()
    )
    cold_controls = tuple(
        cold_exact_lmb_h2_control_v1(
            item.context,
            tuple(occurrence.query for occurrence in item.occurrences),
        )
        for item in results
    )
    no_transfer = tuple(
        run_lmb_no_transfer_control_v1(item.context, cold)
        for item, cold in zip(results, cold_controls)
    )
    wrong = run_lmb_wrong_binding_control_v1(bridge, binding)
    return CrossDomainLMBCampaignV1(
        skeleton_id,
        bridge,
        binding,
        calibration,
        results,
        cold_controls,
        no_transfer,
        wrong,
        (
            run_lmb_semantic_ood_registry_control_v1(
                "hidden_selected_tile_failure_v1"
            ),
            run_lmb_semantic_ood_registry_control_v1(
                "match_arity_four_v1"
            ),
        ),
        lmb_tile_type_permutation_control_v1(
            results[1].context,
            results[1],
        ),
        LMBTransplantControlV1(True, True, True, True, True),
    )


@functools.lru_cache(maxsize=1)
def _cached_cross_domain_lmb_campaign_v1(
    skeleton: Any,
) -> CrossDomainLMBCampaignV1:
    return _run_cross_domain_lmb_campaign_uncached_v1(skeleton)


def run_cross_domain_lmb_campaign_v1(
    skeleton: Any,
    *,
    use_cache: bool = True,
) -> CrossDomainLMBCampaignV1:
    _portable_shape(skeleton)
    return (
        _cached_cross_domain_lmb_campaign_v1(skeleton)
        if use_cache
        else _run_cross_domain_lmb_campaign_uncached_v1(skeleton)
    )


@dataclass(frozen=True, slots=True)
class CrossDomainLMBVerificationV1:
    campaign_id: str
    source_skeleton_identity_checked: bool
    bridge_binding_replayed: bool
    context_chains_replayed: int
    raw_counter_draws_replayed: int
    candidate_counter_blocks_replayed: int
    rejected_counter_blocks_replayed: int
    cold_controls_replayed: int
    controls_checked: int
    same_implementation_replay: bool = True
    independent_algorithm_verification: bool = False
    conditional_random_oracle_assumption_checked: bool = True
    unconditional_iid_claimed: bool = False

    def __post_init__(self) -> None:
        _cid(self.campaign_id, "campaign verification")
        if (
            self.source_skeleton_identity_checked is not True
            or self.bridge_binding_replayed is not True
            or self.context_chains_replayed != 3
            or self.raw_counter_draws_replayed != POSITIVE_DRAW_COUNT
            or self.candidate_counter_blocks_replayed
            != (
                self.raw_counter_draws_replayed
                + self.rejected_counter_blocks_replayed
            )
            or self.rejected_counter_blocks_replayed < 0
            or self.cold_controls_replayed != 3
            or self.controls_checked != 8
            or self.same_implementation_replay is not True
            or self.independent_algorithm_verification is not False
            or self.conditional_random_oracle_assumption_checked is not True
            or self.unconditional_iid_claimed is not False
        ):
            raise CrossDomainLMBInvariantViolation(
                "campaign verification is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_domain_lmb_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "source_skeleton_identity_checked": (
                self.source_skeleton_identity_checked
            ),
            "bridge_binding_replayed": self.bridge_binding_replayed,
            "context_chains_replayed": self.context_chains_replayed,
            "raw_counter_draws_replayed": (
                self.raw_counter_draws_replayed
            ),
            "candidate_counter_blocks_replayed": (
                self.candidate_counter_blocks_replayed
            ),
            "rejected_counter_blocks_replayed": (
                self.rejected_counter_blocks_replayed
            ),
            "cold_controls_replayed": self.cold_controls_replayed,
            "controls_checked": self.controls_checked,
            "same_implementation_replay": self.same_implementation_replay,
            "independent_algorithm_verification": (
                self.independent_algorithm_verification
            ),
            "conditional_random_oracle_assumption_checked": (
                self.conditional_random_oracle_assumption_checked
            ),
            "unconditional_iid_claimed": self.unconditional_iid_claimed,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_cross_domain_lmb_campaign_v1(
    skeleton: Any,
    claimed: CrossDomainLMBCampaignV1,
) -> CrossDomainLMBVerificationV1:
    if type(claimed) is not CrossDomainLMBCampaignV1:
        raise CrossDomainLMBInvariantViolation(
            "campaign verifier rejects runtime substitutions"
        )
    expected = _run_cross_domain_lmb_campaign_uncached_v1(skeleton)
    _runtime_shape(claimed, expected, "cross-domain LMB campaign")
    if claimed.to_document() != expected.to_document():
        raise CrossDomainLMBInvariantViolation(
            "cross-domain LMB campaign differs from full replay"
        )
    traces = tuple(
        trace
        for result in expected.target_results
        for trace in (result.first_trace, result.second_trace)
    )
    return CrossDomainLMBVerificationV1(
        claimed.campaign_id,
        True,
        True,
        3,
        POSITIVE_DRAW_COUNT,
        sum(item.candidate_block_count for item in traces),
        sum(item.rejected_block_count for item in traces),
        3,
        8,
    )


__all__ = [
    "CONTRACT_VERSION",
    "CrossDomainLMBCalibrationV1",
    "CrossDomainLMBCampaignV1",
    "CrossDomainLMBInvariantViolation",
    "CrossDomainLMBVerificationV1",
    "FAMILY_CONFIDENCE_LOWER",
    "FAMILY_TAIL_UPPER",
    "HOEFFDING_RADIUS",
    "LMBAuditOutcome",
    "LMBBridgeLogV1",
    "LMBColdDirectControlV1",
    "LMBCounterSampleTraceV1",
    "LMBEvidenceVerificationV1",
    "LMBPartialStatisticalRAPMV1",
    "LMBRandomnessAssumptionV1",
    "LMBSemanticSupportV1",
    "LMBSlotBindingV1",
    "LMBSoundAuditV1",
    "LMBStatisticalModelRowV1",
    "LMBSupportAuthorizationV1",
    "LMBTargetContextResultV1",
    "LMBTargetContextV1",
    "PER_ATOM_TAIL_UPPER",
    "POSITIVE_DRAW_COUNT",
    "PROFILE_KEY",
    "SAMPLE_COUNT_PER_SUPPORT",
    "SUCCESS_STATUS",
    "acquire_lmb_support_trace_v1",
    "audit_lmb_partial_statistical_rapm_v1",
    "authorize_missing_lmb_support_v1",
    "bind_lmb_relational_slot_v1",
    "cold_exact_lmb_h2_control_v1",
    "cross_domain_lmb_calibration_v1",
    "evaluate_bound_lmb_coordinates_v1",
    "initial_lmb_partial_statistical_rapm_v1",
    "lmb_randomness_assumption_v1",
    "materialize_lmb_relational_state_v1",
    "model_row_from_verified_trace_v1",
    "overlay_lmb_statistical_row_v1",
    "query_neutral_lmb_bridge_log_v1",
    "registered_lmb_target_contexts_v1",
    "run_lmb_no_transfer_control_v1",
    "run_lmb_semantic_ood_registry_control_v1",
    "run_cross_domain_lmb_campaign_v1",
    "run_lmb_target_context_v1",
    "run_lmb_wrong_binding_control_v1",
    "semantic_support_v1",
    "verify_cross_domain_lmb_campaign_v1",
    "verify_lmb_support_trace_v1",
]
