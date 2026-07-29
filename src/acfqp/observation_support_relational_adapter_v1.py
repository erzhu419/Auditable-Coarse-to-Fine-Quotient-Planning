"""Law-free graph observation adapter for portable relational coordinates.

This V0-068 adapter consumes only public topology, symbolic states, exact
legal-action catalogues, and discovery-known realized outcome descriptors.
It never constructs a legacy graph context and never asks a kernel for atoms,
support cardinality, or probabilities.

The frozen V0-066 source skeleton is reconstructed from its exported
content-addressed AST and provenance IDs.  This is consumption of an existing
portable artifact, not a replay of its legacy source construction.

Discovery-known outcomes can be projected into an
``AnonymousRelationalObservationLogV1`` for coordinate *proposal*.  Counts
are normalized only within the known subset.  The omitted ``OTHER`` count is
preserved by the typed wrapper, and both the log and any generated refinement
programs are permanently ineligible to certify transition probabilities or a
plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import functools
import hashlib
from typing import Any, Mapping, Protocol, runtime_checkable

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.portable_relational_skeleton_v1 import (
    AnonymousRelationalObservationLogV1,
    FailedRelationalProofRefV1,
    PortableRelationalProgramV1,
    PortableRelationalRoleSchemaV1,
    PortableRelationalSkeletonV1,
    PortableRelationalSupportSchemaV1,
    RelationalActionSlotV1,
    RelationalObservedRowV1,
    RelationalOutcomeIRV1,
    RelationalProgramContext,
    RelationalProgramType,
    RelationalStateIRV1,
    TargetRelationalProgramGenerationV1,
    evaluate_portable_action_program_v1,
    evaluate_portable_state_program_v1,
    generate_target_relational_programs_v1,
)
from acfqp.transition_tuple_observer_v1 import (
    LegalActionCatalogueV1,
    ObservedJointTransitionV1,
    PublicGraphContextV1,
    SymbolicGraphStateV1,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "observation_support_relational_adapter_v0"

V0066_SOURCE_OBSERVATION_LOG_ID = (
    "c514134c5a8eb08232596d0b6c0666f809227f1f57ddd5a6d36c943f88beeaa4"
)
V0066_SOURCE_SKELETON_ID = (
    "77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322"
)
EXPECTED_BASE_STATE_PROGRAM = "cardinality_actions(legal_actions)"
EXPECTED_BASE_ACTION_PROGRAM = (
    "cardinality_resources("
    "linked_filter(action_anchor,active_resources))"
)

PROPOSAL_ONLY_PROBABILITY_SEMANTICS = (
    "CONDITIONAL_ON_DISCOVERY_KNOWN_OUTCOMES_NOT_A_DYNAMICS_ESTIMATE"
)
OTHER_EXCLUSION_RULE = (
    "OTHER_RETAINED_IN_WRAPPER_AND_EXCLUDED_FROM_COORDINATE_PROPOSAL_LOG"
)


DOMAIN_TAGS = {
    "profile": "acfqp:observation-support-coordinate-profile:v1",
    "outcome": "acfqp:observation-support-discovered-outcome:v1",
    "outcome_count": "acfqp:observation-support-outcome-count:v1",
    "row": "acfqp:observation-support-proposal-row:v1",
    "proposal_log": "acfqp:observation-support-proposal-log:v1",
    "generation": "acfqp:observation-support-proposal-generation:v1",
}


class ObservationSupportRelationalAdapterInvariantViolation(ValueError):
    """A public graph binding or proposal-only provenance invariant failed."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise ObservationSupportRelationalAdapterInvariantViolation(
            str(error)
        ) from error
    return hashlib.sha256(tag + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise ObservationSupportRelationalAdapterInvariantViolation(
            f"{field_name} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "relational probabilities and rewards must be exact Fractions"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _action(value: Any, field_name: str = "action") -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            f"{field_name} must be an exact integer triple"
        )
    return value


def _action_key(action: tuple[int, int, int]) -> str:
    first, second, survivor = _action(action)
    return f"merge:{first}:{second}:{survivor}"


def _oriented_links(
    context: PublicGraphContextV1,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        sorted(
            (anchor, resource)
            for first, second in context.topology.edges
            for anchor, resource in ((first, second), (second, first))
        )
    )


def _public_legal_actions(
    context: PublicGraphContextV1,
    state: SymbolicGraphStateV1,
) -> tuple[tuple[int, int, int], ...]:
    if (
        type(context) is not PublicGraphContextV1
        or type(state) is not SymbolicGraphStateV1
        or len(state.ranks) != context.topology.vertex_count
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "symbolic state/public context binding is invalid"
        )
    if state.failure:
        return ()
    return tuple(
        (first, second, survivor)
        for first, second in context.topology.edges
        if state.ranks[first] > 0
        and state.ranks[first] == state.ranks[second]
        for survivor in (first, second)
    )


def _validate_catalogue(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
) -> None:
    if (
        type(context) is not PublicGraphContextV1
        or type(catalogue) is not LegalActionCatalogueV1
        or catalogue.context_id != context.context_id
        or len(catalogue.state.ranks) != context.topology.vertex_count
        or catalogue.actions
        != _public_legal_actions(context, catalogue.state)
        or catalogue.state.failure != (not catalogue.actions)
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "legal-action catalogue is foreign or not exact public data"
        )


def _slots(
    actions: tuple[tuple[int, int, int], ...],
) -> tuple[RelationalActionSlotV1, ...]:
    return tuple(
        sorted(
            (
                RelationalActionSlotV1(_action_key(action), action[2])
                for action in actions
            ),
            key=lambda item: item.action_slot_id,
        )
    )


def _state_ir_from_public_values(
    context: PublicGraphContextV1,
    state: SymbolicGraphStateV1,
    remaining_horizon: int,
    legal_actions: tuple[tuple[int, int, int], ...],
) -> RelationalStateIRV1:
    if (
        type(context) is not PublicGraphContextV1
        or type(state) is not SymbolicGraphStateV1
        or len(state.ranks) != context.topology.vertex_count
        or type(remaining_horizon) is not int
        or not 0 <= remaining_horizon <= context.horizon
        or type(legal_actions) is not tuple
        or any(_action(item) != item for item in legal_actions)
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "public state-to-IR inputs are invalid"
        )
    exact_actions = _public_legal_actions(context, state)
    expected_actions = (
        ()
        if state.failure or remaining_horizon == 0
        else exact_actions
    )
    if legal_actions != expected_actions:
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "declared legal actions differ from public topology/state"
        )
    if state.failure:
        terminal_kind = "FAILURE"
    elif remaining_horizon == 0:
        terminal_kind = "HORIZON_TERMINAL"
    else:
        terminal_kind = "ACTIVE"
    return RelationalStateIRV1(
        structural_context_id=context.context_id,
        remaining_horizon=remaining_horizon,
        resource_attributes=state.ranks,
        active_resources=tuple(
            index for index, rank in enumerate(state.ranks) if rank > 0
        ),
        linked_pairs=_oriented_links(context),
        legal_actions=_slots(legal_actions),
        terminal_kind=terminal_kind,
    )


def relational_state_ir_v1(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
) -> RelationalStateIRV1:
    """Adapt a complete public catalogue without consulting dynamics."""

    _validate_catalogue(context, catalogue)
    return _state_ir_from_public_values(
        context,
        catalogue.state,
        catalogue.remaining_horizon,
        catalogue.actions,
    )


def _primitive(
    operation: str,
    result_type: RelationalProgramType,
    context: RelationalProgramContext,
) -> PortableRelationalProgramV1:
    return PortableRelationalProgramV1(
        operation=operation,
        result_type=result_type,
        context=context,
    )


@functools.lru_cache(maxsize=1)
def v0066_source_skeleton_v1() -> PortableRelationalSkeletonV1:
    """Recreate the frozen exported V0-066 skeleton, without source replay."""

    legal_actions = _primitive(
        "legal_actions",
        RelationalProgramType.ACTION_SET,
        RelationalProgramContext.STATE,
    )
    state_program = PortableRelationalProgramV1(
        operation="cardinality_actions",
        result_type=RelationalProgramType.INTEGER,
        context=RelationalProgramContext.STATE,
        arguments=(legal_actions,),
    )
    action_anchor = _primitive(
        "action_anchor",
        RelationalProgramType.ANCHOR,
        RelationalProgramContext.STATE_ACTION,
    )
    active_resources = _primitive(
        "active_resources",
        RelationalProgramType.RESOURCE_SET,
        RelationalProgramContext.STATE,
    )
    linked_active = PortableRelationalProgramV1(
        operation="linked_filter",
        result_type=RelationalProgramType.RESOURCE_SET,
        context=RelationalProgramContext.STATE_ACTION,
        arguments=(action_anchor, active_resources),
    )
    action_program = PortableRelationalProgramV1(
        operation="cardinality_resources",
        result_type=RelationalProgramType.INTEGER,
        context=RelationalProgramContext.STATE_ACTION,
        arguments=(linked_active,),
    )
    skeleton = PortableRelationalSkeletonV1(
        role_schema_id=PortableRelationalRoleSchemaV1().role_schema_id,
        source_observation_log_id=V0066_SOURCE_OBSERVATION_LOG_ID,
        state_program=state_program,
        action_program=action_program,
        support_schema=PortableRelationalSupportSchemaV1(),
    )
    if (
        skeleton.skeleton_id != V0066_SOURCE_SKELETON_ID
        or skeleton.state_program.rendered != EXPECTED_BASE_STATE_PROGRAM
        or skeleton.action_program.rendered != EXPECTED_BASE_ACTION_PROGRAM
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "frozen V0-066 skeleton reconstruction changed"
        )
    return skeleton


@dataclass(frozen=True, slots=True)
class ObservationSupportCoordinateProfileV1:
    """Selected portable programs used to tag states and semantic actions."""

    skeleton_id: str
    state_programs: tuple[PortableRelationalProgramV1, ...]
    action_programs: tuple[PortableRelationalProgramV1, ...]
    refinement_generation_id: str | None = None
    proposal_only_refinement: bool = False

    def __post_init__(self) -> None:
        _cid(self.skeleton_id, "coordinate-profile skeleton")
        if (
            type(self.state_programs) is not tuple
            or not self.state_programs
            or any(
                type(item) is not PortableRelationalProgramV1
                or item.context is not RelationalProgramContext.STATE
                for item in self.state_programs
            )
            or type(self.action_programs) is not tuple
            or not self.action_programs
            or any(
                type(item) is not PortableRelationalProgramV1
                or item.context is not RelationalProgramContext.STATE_ACTION
                for item in self.action_programs
            )
            or len({item.program_id for item in self.state_programs})
            != len(self.state_programs)
            or len({item.program_id for item in self.action_programs})
            != len(self.action_programs)
            or type(self.proposal_only_refinement) is not bool
            or (
                self.refinement_generation_id is None
                and self.proposal_only_refinement
            )
            or (
                self.refinement_generation_id is not None
                and not self.proposal_only_refinement
            )
        ):
            raise ObservationSupportRelationalAdapterInvariantViolation(
                "observation-support coordinate profile is invalid"
            )
        if self.refinement_generation_id is not None:
            _cid(self.refinement_generation_id, "refinement generation")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_coordinate_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "skeleton_id": self.skeleton_id,
            "state_programs": [
                item.to_document() for item in self.state_programs
            ],
            "action_programs": [
                item.to_document() for item in self.action_programs
            ],
            "refinement_generation_id": self.refinement_generation_id,
            "proposal_only_refinement": self.proposal_only_refinement,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def base_coordinate_profile_v1(
    skeleton: PortableRelationalSkeletonV1 | None = None,
) -> ObservationSupportCoordinateProfileV1:
    selected = v0066_source_skeleton_v1() if skeleton is None else skeleton
    if (
        type(selected) is not PortableRelationalSkeletonV1
        or selected.skeleton_id != V0066_SOURCE_SKELETON_ID
        or selected.state_program.rendered != EXPECTED_BASE_STATE_PROGRAM
        or selected.action_program.rendered != EXPECTED_BASE_ACTION_PROGRAM
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "base profile requires the exact frozen V0-066 skeleton"
        )
    return ObservationSupportCoordinateProfileV1(
        skeleton_id=selected.skeleton_id,
        state_programs=(selected.state_program,),
        action_programs=(selected.action_program,),
    )


TaggedCoordinate = tuple[tuple[str, Any], ...]
SupportCoordinate = tuple[int, TaggedCoordinate, TaggedCoordinate]


def state_coordinate_v1(
    profile: ObservationSupportCoordinateProfileV1,
    state: RelationalStateIRV1,
) -> TaggedCoordinate:
    if (
        type(profile) is not ObservationSupportCoordinateProfileV1
        or type(state) is not RelationalStateIRV1
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "state coordinate binding is invalid"
        )
    return tuple(
        evaluate_portable_state_program_v1(program, state)
        for program in profile.state_programs
    )


def action_slot_v1(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> RelationalActionSlotV1:
    state = relational_state_ir_v1(context, catalogue)
    key = _action_key(action)
    for slot in state.legal_actions:
        if slot.opaque_action_key == key:
            return slot
    raise ObservationSupportRelationalAdapterInvariantViolation(
        "action is absent from the bound public catalogue"
    )


def action_coordinate_v1(
    profile: ObservationSupportCoordinateProfileV1,
    state: RelationalStateIRV1,
    action: RelationalActionSlotV1,
) -> TaggedCoordinate:
    if (
        type(profile) is not ObservationSupportCoordinateProfileV1
        or type(state) is not RelationalStateIRV1
        or type(action) is not RelationalActionSlotV1
        or action not in state.legal_actions
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "action coordinate binding is invalid"
        )
    return tuple(
        evaluate_portable_action_program_v1(program, state, action)
        for program in profile.action_programs
    )


def support_coordinate_v1(
    profile: ObservationSupportCoordinateProfileV1,
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> SupportCoordinate:
    state = relational_state_ir_v1(context, catalogue)
    slot = action_slot_v1(context, catalogue, action)
    return (
        catalogue.remaining_horizon,
        state_coordinate_v1(profile, state),
        action_coordinate_v1(profile, state, slot),
    )


class DiscoveryOutcomeKind(str, Enum):
    DISCOVERED = "DISCOVERED"


@dataclass(frozen=True, slots=True)
class DiscoveryKnownOutcomeDescriptorV1:
    """One realized joint outcome identity and its public relational fields."""

    outcome_id: str
    context_id: str
    source_catalogue_id: str
    source_action: tuple[int, int, int]
    next_state: SymbolicGraphStateV1
    next_remaining_horizon: int
    next_legal_actions: tuple[tuple[int, int, int], ...]
    normalized_reward: Fraction
    failure: bool
    terminal: bool
    outcome_kind: DiscoveryOutcomeKind = DiscoveryOutcomeKind.DISCOVERED

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.outcome_id, "discovered outcome"),
            (self.context_id, "discovered outcome context"),
            (self.source_catalogue_id, "discovered outcome catalogue"),
        ):
            _cid(value, field_name)
        _action(self.source_action, "discovered outcome source action")
        if (
            type(self.next_state) is not SymbolicGraphStateV1
            or type(self.next_remaining_horizon) is not int
            or not 0 <= self.next_remaining_horizon <= 1
            or type(self.next_legal_actions) is not tuple
            or any(
                _action(item, "successor legal action") != item
                for item in self.next_legal_actions
            )
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or self.terminal
            != (self.failure or self.next_remaining_horizon == 0)
            or type(self.outcome_kind) is not DiscoveryOutcomeKind
            or self.outcome_kind is not DiscoveryOutcomeKind.DISCOVERED
        ):
            raise ObservationSupportRelationalAdapterInvariantViolation(
                "discovery-known outcome descriptor is invalid"
            )
        if self.outcome_id != _content_id("outcome", self._semantic_payload()):
            raise ObservationSupportRelationalAdapterInvariantViolation(
                "discovered outcome ID does not bind its semantic tuple"
            )

    def _semantic_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_discovered_outcome.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "context_id": self.context_id,
            "source_catalogue_id": self.source_catalogue_id,
            "source_action": list(self.source_action),
            "next_state": self.next_state.to_document(),
            "next_remaining_horizon": self.next_remaining_horizon,
            "next_legal_actions": [
                list(item) for item in self.next_legal_actions
            ],
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "outcome_kind": self.outcome_kind.value,
        }

    def to_document(self) -> dict[str, Any]:
        return {**self._semantic_payload(), "outcome_id": self.outcome_id}


def discovered_outcome_descriptor_v1(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
    next_state: SymbolicGraphStateV1,
    normalized_reward: Fraction,
    failure: bool,
    terminal: bool,
) -> DiscoveryKnownOutcomeDescriptorV1:
    """Freeze one observed tuple using only public state/action semantics."""

    _validate_catalogue(context, catalogue)
    _action(action)
    if action not in catalogue.actions:
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "observed outcome source action is not in its catalogue"
        )
    if (
        type(next_state) is not SymbolicGraphStateV1
        or len(next_state.ranks) != context.topology.vertex_count
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "observed successor is outside its public context"
        )
    next_remaining = catalogue.remaining_horizon - 1
    raw_actions = _public_legal_actions(
        context,
        SymbolicGraphStateV1(next_state.ranks, False),
    )
    expected_failure = not raw_actions
    expected_actions = (
        ()
        if expected_failure or next_remaining == 0
        else raw_actions
    )
    if (
        failure is not expected_failure
        or next_state.failure is not expected_failure
        or terminal is not (expected_failure or next_remaining == 0)
        or type(normalized_reward) is not Fraction
        or not 0 <= normalized_reward <= 1
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "observed successor flags disagree with public legal actions"
        )
    provisional = {
        "schema": "acfqp.observation_support_discovered_outcome.v1",
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "context_id": context.context_id,
        "source_catalogue_id": catalogue.catalogue_id,
        "source_action": list(action),
        "next_state": next_state.to_document(),
        "next_remaining_horizon": next_remaining,
        "next_legal_actions": [list(item) for item in expected_actions],
        "normalized_reward": _fdoc(normalized_reward),
        "failure": failure,
        "terminal": terminal,
        "outcome_kind": DiscoveryOutcomeKind.DISCOVERED.value,
    }
    return DiscoveryKnownOutcomeDescriptorV1(
        outcome_id=_content_id("outcome", provisional),
        context_id=context.context_id,
        source_catalogue_id=catalogue.catalogue_id,
        source_action=action,
        next_state=next_state,
        next_remaining_horizon=next_remaining,
        next_legal_actions=expected_actions,
        normalized_reward=normalized_reward,
        failure=failure,
        terminal=terminal,
    )


def descriptor_from_observed_transition_v1(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
    observation: ObservedJointTransitionV1,
) -> DiscoveryKnownOutcomeDescriptorV1:
    if (
        type(observation) is not ObservedJointTransitionV1
        or observation.context_id != context.context_id
        or observation.catalogue_id != catalogue.catalogue_id
        or observation.source_state != catalogue.state
        or observation.remaining_horizon != catalogue.remaining_horizon
        or observation.action != action
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "observed transition is transplanted across its source row"
        )
    return discovered_outcome_descriptor_v1(
        context,
        catalogue,
        action,
        observation.next_state,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    )


@dataclass(frozen=True, slots=True)
class DiscoveryKnownOutcomeCountV1:
    descriptor: DiscoveryKnownOutcomeDescriptorV1
    count: int

    def __post_init__(self) -> None:
        if (
            type(self.descriptor) is not DiscoveryKnownOutcomeDescriptorV1
            or type(self.count) is not int
            or self.count <= 0
        ):
            raise ObservationSupportRelationalAdapterInvariantViolation(
                "discovery-known outcome count is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_outcome_count.v1",
            "schema_version": SCHEMA_VERSION,
            "descriptor": self.descriptor.to_document(),
            "count": self.count,
            "probability_evidence_draw_count": 0,
        }

    @property
    def outcome_count_id(self) -> str:
        return _content_id("outcome_count", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_count_id": self.outcome_count_id}


@runtime_checkable
class DiscoveryKnownRelationalRowProtocol(Protocol):
    @property
    def support_epoch_id(self) -> str: ...

    @property
    def catalogue(self) -> LegalActionCatalogueV1: ...

    @property
    def action(self) -> tuple[int, int, int]: ...

    @property
    def discovered_outcomes(
        self,
    ) -> tuple[DiscoveryKnownOutcomeCountV1, ...]: ...

    @property
    def other_count(self) -> int: ...


@dataclass(frozen=True, slots=True)
class DiscoveryKnownRelationalRowV1:
    support_epoch_id: str
    catalogue: LegalActionCatalogueV1
    action: tuple[int, int, int]
    discovered_outcomes: tuple[DiscoveryKnownOutcomeCountV1, ...]
    other_count: int

    def __post_init__(self) -> None:
        _cid(self.support_epoch_id, "row support epoch")
        _action(self.action)
        if (
            type(self.catalogue) is not LegalActionCatalogueV1
            or self.action not in self.catalogue.actions
            or type(self.discovered_outcomes) is not tuple
            or not self.discovered_outcomes
            or any(
                type(item) is not DiscoveryKnownOutcomeCountV1
                for item in self.discovered_outcomes
            )
            or tuple(
                item.descriptor.outcome_id for item in self.discovered_outcomes
            )
            != tuple(
                sorted(
                    {
                        item.descriptor.outcome_id
                        for item in self.discovered_outcomes
                    }
                )
            )
            or type(self.other_count) is not int
            or self.other_count < 0
        ):
            raise ObservationSupportRelationalAdapterInvariantViolation(
                "proposal row is malformed or contains duplicate outcomes"
            )
        for item in self.discovered_outcomes:
            descriptor = item.descriptor
            if (
                descriptor.context_id != self.catalogue.context_id
                or descriptor.source_catalogue_id
                != self.catalogue.catalogue_id
                or descriptor.source_action != self.action
            ):
                raise ObservationSupportRelationalAdapterInvariantViolation(
                    "proposal outcome is transplanted across a source row"
                )

    @property
    def known_count(self) -> int:
        return sum(item.count for item in self.discovered_outcomes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_proposal_row.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "support_epoch_id": self.support_epoch_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "action": list(self.action),
            "discovered_outcomes": [
                item.to_document() for item in self.discovered_outcomes
            ],
            "known_count": self.known_count,
            "other_count": self.other_count,
            "probability_evidence_draw_count": 0,
            "certificate_eligible": False,
        }

    @property
    def proposal_row_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_row_id": self.proposal_row_id}


def _freeze_row_protocol(
    row: DiscoveryKnownRelationalRowProtocol,
) -> DiscoveryKnownRelationalRowV1:
    if not isinstance(row, DiscoveryKnownRelationalRowProtocol):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "proposal row does not implement the small row protocol"
        )
    if type(row) is DiscoveryKnownRelationalRowV1:
        return row
    return DiscoveryKnownRelationalRowV1(
        support_epoch_id=row.support_epoch_id,
        catalogue=row.catalogue,
        action=row.action,
        discovered_outcomes=row.discovered_outcomes,
        other_count=row.other_count,
    )


def _validate_descriptor_in_context(
    context: PublicGraphContextV1,
    row: DiscoveryKnownRelationalRowV1,
    descriptor: DiscoveryKnownOutcomeDescriptorV1,
) -> RelationalStateIRV1:
    expected = discovered_outcome_descriptor_v1(
        context,
        row.catalogue,
        row.action,
        descriptor.next_state,
        descriptor.normalized_reward,
        descriptor.failure,
        descriptor.terminal,
    )
    if expected != descriptor:
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "proposal descriptor does not replay from public semantics"
        )
    return _state_ir_from_public_values(
        context,
        descriptor.next_state,
        descriptor.next_remaining_horizon,
        descriptor.next_legal_actions,
    )


@dataclass(frozen=True, slots=True)
class ProposalOnlyAnonymousRelationalLogV1:
    """A portable log whose known-only weights cannot certify dynamics."""

    context_id: str
    source_skeleton_id: str
    proposal_rows: tuple[DiscoveryKnownRelationalRowV1, ...]
    anonymous_log: AnonymousRelationalObservationLogV1
    row_projection_bindings: tuple[tuple[str, str], ...]
    known_draw_count: int
    excluded_other_draw_count: int
    rows_with_other: int
    proposal_only_probability_semantics: str = (
        PROPOSAL_ONLY_PROBABILITY_SEMANTICS
    )
    other_exclusion_rule: str = OTHER_EXCLUSION_RULE
    coordinate_proposal_eligible: bool = True
    dynamics_certificate_eligible: bool = False
    plan_certificate_eligible: bool = False

    def __post_init__(self) -> None:
        _cid(self.context_id, "proposal-log context")
        _cid(self.source_skeleton_id, "proposal-log source skeleton")
        if (
            self.source_skeleton_id != V0066_SOURCE_SKELETON_ID
            or type(self.proposal_rows) is not tuple
            or not self.proposal_rows
            or any(
                type(item) is not DiscoveryKnownRelationalRowV1
                for item in self.proposal_rows
            )
            or tuple(item.proposal_row_id for item in self.proposal_rows)
            != tuple(
                sorted(
                    {item.proposal_row_id for item in self.proposal_rows}
                )
            )
            or type(self.anonymous_log)
            is not AnonymousRelationalObservationLogV1
            or len(self.anonymous_log.rows) != len(self.proposal_rows)
            or type(self.row_projection_bindings) is not tuple
            or self.row_projection_bindings
            != tuple(sorted(set(self.row_projection_bindings)))
            or {
                item[0] for item in self.row_projection_bindings
            }
            != {item.proposal_row_id for item in self.proposal_rows}
            or {
                item[1] for item in self.row_projection_bindings
            }
            != {item.observed_row_id for item in self.anonymous_log.rows}
            or any(
                type(item) is not tuple
                or len(item) != 2
                or _cid(item[0], "proposal row binding") != item[0]
                or _cid(item[1], "observed row binding") != item[1]
                for item in self.row_projection_bindings
            )
            or self.known_draw_count
            != sum(item.known_count for item in self.proposal_rows)
            or self.excluded_other_draw_count
            != sum(item.other_count for item in self.proposal_rows)
            or self.rows_with_other
            != sum(item.other_count > 0 for item in self.proposal_rows)
            or self.proposal_only_probability_semantics
            != PROPOSAL_ONLY_PROBABILITY_SEMANTICS
            or self.other_exclusion_rule != OTHER_EXCLUSION_RULE
            or self.coordinate_proposal_eligible is not True
            or self.dynamics_certificate_eligible is not False
            or self.plan_certificate_eligible is not False
        ):
            raise ObservationSupportRelationalAdapterInvariantViolation(
                "proposal-only anonymous log changed its claim boundary"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_proposal_log.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "source_skeleton_id": self.source_skeleton_id,
            "proposal_row_ids": [
                item.proposal_row_id for item in self.proposal_rows
            ],
            "anonymous_observation_log_id": (
                self.anonymous_log.observation_log_id
            ),
            "row_projection_bindings": [
                {
                    "proposal_row_id": proposal_row_id,
                    "observed_row_id": observed_row_id,
                }
                for proposal_row_id, observed_row_id
                in self.row_projection_bindings
            ],
            "known_draw_count": self.known_draw_count,
            "excluded_other_draw_count": self.excluded_other_draw_count,
            "rows_with_other": self.rows_with_other,
            "proposal_only_probability_semantics": (
                self.proposal_only_probability_semantics
            ),
            "other_exclusion_rule": self.other_exclusion_rule,
            "coordinate_proposal_eligible": True,
            "dynamics_certificate_eligible": False,
            "plan_certificate_eligible": False,
        }

    @property
    def proposal_log_id(self) -> str:
        return _content_id("proposal_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_log_id": self.proposal_log_id}


def build_proposal_only_relational_observation_log_v1(
    context: PublicGraphContextV1,
    rows: tuple[DiscoveryKnownRelationalRowProtocol, ...],
    skeleton: PortableRelationalSkeletonV1 | None = None,
) -> ProposalOnlyAnonymousRelationalLogV1:
    """Project discovery-known outcomes; retain but never materialize OTHER."""

    if type(context) is not PublicGraphContextV1 or type(rows) is not tuple:
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "proposal-log context/rows have invalid concrete types"
        )
    selected_skeleton = (
        v0066_source_skeleton_v1() if skeleton is None else skeleton
    )
    base_coordinate_profile_v1(selected_skeleton)
    frozen_rows = tuple(_freeze_row_protocol(item) for item in rows)
    relational_rows: list[RelationalObservedRowV1] = []
    for row in frozen_rows:
        _validate_catalogue(context, row.catalogue)
        state = relational_state_ir_v1(context, row.catalogue)
        slot = action_slot_v1(context, row.catalogue, row.action)
        outcomes = tuple(
            sorted(
                (
                    RelationalOutcomeIRV1(
                        next_state=_validate_descriptor_in_context(
                            context,
                            row,
                            item.descriptor,
                        ),
                        probability=Fraction(item.count, row.known_count),
                        normalized_reward=item.descriptor.normalized_reward,
                        failure=item.descriptor.failure,
                        terminal=item.descriptor.terminal,
                    )
                    for item in row.discovered_outcomes
                ),
                key=lambda item: item.outcome_ir_id,
            )
        )
        relational_rows.append(RelationalObservedRowV1(state, slot, outcomes))
    bindings = tuple(
        sorted(
            (
                proposal.proposal_row_id,
                observed.observed_row_id,
            )
            for proposal, observed in zip(frozen_rows, relational_rows)
        )
    )
    ordered_proposals = tuple(
        sorted(frozen_rows, key=lambda item: item.proposal_row_id)
    )
    anonymous = AnonymousRelationalObservationLogV1(
        PortableRelationalRoleSchemaV1(),
        tuple(
            sorted(
                relational_rows,
                key=lambda item: item.observed_row_id,
            )
        ),
    )
    return ProposalOnlyAnonymousRelationalLogV1(
        context_id=context.context_id,
        source_skeleton_id=selected_skeleton.skeleton_id,
        proposal_rows=ordered_proposals,
        anonymous_log=anonymous,
        row_projection_bindings=bindings,
        known_draw_count=sum(item.known_count for item in ordered_proposals),
        excluded_other_draw_count=sum(
            item.other_count for item in ordered_proposals
        ),
        rows_with_other=sum(item.other_count > 0 for item in ordered_proposals),
    )


@dataclass(frozen=True, slots=True)
class ProposalOnlyRelationalProgramGenerationV1:
    proposal_log_id: str
    portable_generation: TargetRelationalProgramGenerationV1
    state_coordinate_candidates: tuple[PortableRelationalProgramV1, ...]
    action_coordinate_candidates: tuple[PortableRelationalProgramV1, ...]
    coordinate_proposal_eligible: bool = True
    dynamics_certificate_eligible: bool = False
    plan_certificate_eligible: bool = False

    def __post_init__(self) -> None:
        _cid(self.proposal_log_id, "proposal-only generation log")
        if (
            type(self.portable_generation)
            is not TargetRelationalProgramGenerationV1
            or type(self.state_coordinate_candidates) is not tuple
            or type(self.action_coordinate_candidates) is not tuple
            or any(
                type(item) is not PortableRelationalProgramV1
                or item.context is not RelationalProgramContext.STATE
                or item.result_type
                not in (
                    RelationalProgramType.INTEGER,
                    RelationalProgramType.SIGNATURE,
                )
                for item in self.state_coordinate_candidates
            )
            or any(
                type(item) is not PortableRelationalProgramV1
                or item.context is not RelationalProgramContext.STATE_ACTION
                or item.result_type is not RelationalProgramType.INTEGER
                for item in self.action_coordinate_candidates
            )
            or self.coordinate_proposal_eligible is not True
            or self.dynamics_certificate_eligible is not False
            or self.plan_certificate_eligible is not False
        ):
            raise ObservationSupportRelationalAdapterInvariantViolation(
                "proposal-only target program generation is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.observation_support_proposal_generation.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "proposal_log_id": self.proposal_log_id,
            "portable_generation_id": self.portable_generation.generation_id,
            "state_coordinate_candidate_ids": [
                item.program_id for item in self.state_coordinate_candidates
            ],
            "action_coordinate_candidate_ids": [
                item.program_id for item in self.action_coordinate_candidates
            ],
            "coordinate_proposal_eligible": True,
            "dynamics_certificate_eligible": False,
            "plan_certificate_eligible": False,
        }

    @property
    def proposal_generation_id(self) -> str:
        return _content_id("generation", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "proposal_generation_id": self.proposal_generation_id,
        }


def generate_proposal_only_relational_candidates_v1(
    skeleton: PortableRelationalSkeletonV1,
    failed_proof: FailedRelationalProofRefV1,
    proposal_log: ProposalOnlyAnonymousRelationalLogV1,
) -> ProposalOnlyRelationalProgramGenerationV1:
    """Generate fresh target coordinates, preserving the no-certificate type."""

    if (
        type(skeleton) is not PortableRelationalSkeletonV1
        or skeleton.skeleton_id != V0066_SOURCE_SKELETON_ID
        or type(failed_proof) is not FailedRelationalProofRefV1
        or type(proposal_log) is not ProposalOnlyAnonymousRelationalLogV1
        or failed_proof.target_context_id != proposal_log.context_id
        or proposal_log.source_skeleton_id != skeleton.skeleton_id
    ):
        raise ObservationSupportRelationalAdapterInvariantViolation(
            "proposal-only target generation binding is invalid"
        )
    generation = generate_target_relational_programs_v1(
        skeleton,
        failed_proof,
        proposal_log.anonymous_log,
    )
    state = tuple(
        item
        for item in generation.registry.programs
        if item.context is RelationalProgramContext.STATE
        and item.result_type
        in (
            RelationalProgramType.INTEGER,
            RelationalProgramType.SIGNATURE,
        )
        and item.program_id != skeleton.state_program.program_id
    )
    action = tuple(
        item
        for item in generation.registry.programs
        if item.context is RelationalProgramContext.STATE_ACTION
        and item.result_type is RelationalProgramType.INTEGER
        and item.program_id != skeleton.action_program.program_id
    )
    return ProposalOnlyRelationalProgramGenerationV1(
        proposal_log_id=proposal_log.proposal_log_id,
        portable_generation=generation,
        state_coordinate_candidates=state,
        action_coordinate_candidates=action,
    )


__all__ = [
    "CONTRACT_VERSION",
    "DiscoveryKnownOutcomeCountV1",
    "DiscoveryKnownOutcomeDescriptorV1",
    "DiscoveryKnownRelationalRowProtocol",
    "DiscoveryKnownRelationalRowV1",
    "ObservationSupportCoordinateProfileV1",
    "ObservationSupportRelationalAdapterInvariantViolation",
    "PROFILE_KEY",
    "ProposalOnlyAnonymousRelationalLogV1",
    "ProposalOnlyRelationalProgramGenerationV1",
    "SCHEMA_VERSION",
    "V0066_SOURCE_OBSERVATION_LOG_ID",
    "V0066_SOURCE_SKELETON_ID",
    "action_coordinate_v1",
    "action_slot_v1",
    "base_coordinate_profile_v1",
    "build_proposal_only_relational_observation_log_v1",
    "descriptor_from_observed_transition_v1",
    "discovered_outcome_descriptor_v1",
    "generate_proposal_only_relational_candidates_v1",
    "relational_state_ir_v1",
    "state_coordinate_v1",
    "support_coordinate_v1",
    "v0066_source_skeleton_v1",
]
