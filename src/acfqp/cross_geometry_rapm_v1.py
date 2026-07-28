"""Target-local statistical RAPMs for held-out graph geometries.

V0-065 transports only a source-observed relational AST and support-key
schema.  Every held-out graph instantiates its own supports, acquires its own
generative observations, and replans inside its own interval RAPM.  A failed
Diamond certificate may select one additional state and action program from
the source-frozen registry; no target program or primitive is generated.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import functools
import hashlib
from itertools import product
from typing import Any, Mapping

from acfqp.domains.g2048 import G2048Action, G2048State, G2048Status
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.relational_graph_core_v1 import (
    GraphActionViewV1,
    GraphCoordinateProgramV1,
    GraphObservedRowV1,
    GraphOutcomeViewV1,
    GraphProgramContext,
    GraphProgramRegistryV1,
    GraphProgramType,
    GraphStateViewV1,
    GraphTopologyV1,
    RelationalGraphCoordinateProposalV1,
    evaluate_action_coordinate_v1,
    evaluate_state_coordinate_v1,
    generate_relational_graph_program_registry_v1,
    relational_graph_synthesis_metrics_v1,
    synthesize_relational_graph_proposal_v1,
    verify_relational_graph_proposal_v1,
)
from acfqp.cross_graph_relational_support_v1 import (
    CONTRACT_VERSION,
    HORIZON,
    PROFILE_KEY,
    RISK_TOLERANCE,
    ColdExactH2ControlV1,
    CrossGraphFamilyV1,
    CrossGraphSourceObservationBundleV1,
    CrossGraphSplit,
    CrossGraphStateCatalogueV1,
    CrossGraphStructuralContextV1,
    GraphMergeKernelV1,
    acquire_cross_graph_source_observations_v1,
    cold_exact_h2_oracle_v1,
    continuation_catalogues_from_states_v1,
    _complete_h2_rows,
    registered_cross_graph_family_v1,
    target_root_catalogues_v1,
)


SCHEMA_VERSION = "1.0.0"
SUCCESS_STATUS = "CERTIFIED_REGISTERED_CROSS_GEOMETRY_RELATIONAL_RAPM_FAMILY"
SAMPLE_COUNT_PER_GROUND_ROW = 65_536
HOEFFDING_RADIUS = Fraction(1, 110)
PER_ATOM_TAIL_UPPER = Fraction(1, 25_000)
MAX_STRUCTURAL_ATOMS_PER_ROW = 4
POSITIVE_TARGET_GROUND_ROWS = 180
SEMANTIC_OOD_GROUND_ROWS = 48
PREREGISTERED_ATOM_OBLIGATIONS = (
    (POSITIVE_TARGET_GROUND_ROWS + SEMANTIC_OOD_GROUND_ROWS)
    * MAX_STRUCTURAL_ATOMS_PER_ROW
)
FAMILY_TAIL_UPPER = (
    PREREGISTERED_ATOM_OBLIGATIONS * PER_ATOM_TAIL_UPPER
)
FAMILY_CONFIDENCE_LOWER = 1 - FAMILY_TAIL_UPPER

DOMAIN_TAGS = {
    "profile": "acfqp:cross-geometry-coordinate-profile:v1",
    "support": "acfqp:cross-geometry-semantic-support:v1",
    "atom": "acfqp:cross-geometry-symbolic-atom:v1",
    "authorization": "acfqp:cross-geometry-authorization:v1",
    "sampled_row": "acfqp:cross-geometry-sampled-row:v1",
    "evidence": "acfqp:cross-geometry-evidence:v1",
    "evidence_verification": "acfqp:cross-geometry-evidence-verification:v1",
    "interval": "acfqp:cross-geometry-interval:v1",
    "model_row": "acfqp:cross-geometry-model-row:v1",
    "model": "acfqp:cross-geometry-rapm:v1",
    "decision": "acfqp:cross-geometry-abstract-decision:v1",
    "audit": "acfqp:cross-geometry-model-audit:v1",
    "refinement": "acfqp:cross-geometry-refinement-trace:v1",
    "occurrence": "acfqp:cross-geometry-occurrence:v1",
    "target_result": "acfqp:cross-geometry-target-result:v1",
    "legacy": "acfqp:cross-geometry-legacy-control:v1",
    "no_transfer": "acfqp:cross-geometry-no-transfer-control:v1",
    "ood": "acfqp:cross-geometry-semantic-ood-control:v1",
    "permutation": "acfqp:cross-geometry-permutation-control:v1",
    "calibration": "acfqp:cross-geometry-calibration:v1",
    "campaign": "acfqp:cross-geometry-campaign:v1",
    "verification": "acfqp:cross-geometry-verification:v1",
}


class CrossGeometryInvariantViolation(ValueError):
    """A proposal, target row, model, proof, or identity chain is invalid."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise CrossGeometryInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode() + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise CrossGeometryInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _jsonable(value: Any) -> Any:
    if type(value) is tuple:
        return [_jsonable(item) for item in value]
    if type(value) is list:
        return [_jsonable(item) for item in value]
    if type(value) is dict:
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


TaggedValue = tuple[str, Any]
StateCoordinate = tuple[TaggedValue, ...]
ActionCoordinate = tuple[TaggedValue, ...]
Destination = tuple[Any, ...]


@dataclass(frozen=True, slots=True)
class CoordinateProfileV1:
    proposal_id: str
    program_registry_id: str
    state_programs: tuple[GraphCoordinateProgramV1, ...]
    action_programs: tuple[GraphCoordinateProgramV1, ...]
    refinement_index: int
    selected_after_failed_audit_id: str | None

    def __post_init__(self) -> None:
        _cid(self.proposal_id, "profile proposal")
        _cid(self.program_registry_id, "profile registry")
        if (
            type(self.state_programs) is not tuple
            or not self.state_programs
            or any(
                type(item) is not GraphCoordinateProgramV1
                or item.context is not GraphProgramContext.STATE
                for item in self.state_programs
            )
            or type(self.action_programs) is not tuple
            or not self.action_programs
            or any(
                type(item) is not GraphCoordinateProgramV1
                or item.context is not GraphProgramContext.STATE_ACTION
                for item in self.action_programs
            )
            or len({item.program_id for item in self.state_programs})
            != len(self.state_programs)
            or len({item.program_id for item in self.action_programs})
            != len(self.action_programs)
            or type(self.refinement_index) is not int
            or self.refinement_index not in (0, 1)
            or (
                self.refinement_index == 0
                and (
                    len(self.state_programs) != 1
                    or len(self.action_programs) != 1
                    or self.selected_after_failed_audit_id is not None
                )
            )
            or (
                self.refinement_index == 1
                and (
                    len(self.state_programs) != 2
                    or len(self.action_programs) != 2
                    or self.selected_after_failed_audit_id is None
                )
            )
        ):
            raise CrossGeometryInvariantViolation(
                "coordinate profile shape or chronology changed"
            )
        if self.selected_after_failed_audit_id is not None:
            _cid(
                self.selected_after_failed_audit_id,
                "profile failed audit",
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_coordinate_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposal_id": self.proposal_id,
            "program_registry_id": self.program_registry_id,
            "state_programs": [
                item.to_document() for item in self.state_programs
            ],
            "action_programs": [
                item.to_document() for item in self.action_programs
            ],
            "refinement_index": self.refinement_index,
            "selected_after_failed_audit_id": (
                self.selected_after_failed_audit_id
            ),
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "profile_id": self.profile_id}


def _state_coordinate(
    profile: CoordinateProfileV1,
    context: CrossGraphStructuralContextV1,
    state: GraphStateViewV1,
) -> StateCoordinate:
    return tuple(
        evaluate_state_coordinate_v1(program, context.topology, state)
        for program in profile.state_programs
    )


def _action_coordinate(
    profile: CoordinateProfileV1,
    context: CrossGraphStructuralContextV1,
    catalogue: CrossGraphStateCatalogueV1,
    action: GraphActionViewV1,
) -> ActionCoordinate:
    return tuple(
        evaluate_action_coordinate_v1(
            program,
            context.topology,
            catalogue.state,
            action,
            catalogue.legal_actions,
        )
        for program in profile.action_programs
    )


@dataclass(frozen=True, slots=True)
class SemanticSupportKeyV1:
    remaining_horizon: int
    state_coordinate: StateCoordinate
    action_coordinate: ActionCoordinate

    def __post_init__(self) -> None:
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, HORIZON)
            or type(self.state_coordinate) is not tuple
            or not self.state_coordinate
            or type(self.action_coordinate) is not tuple
            or not self.action_coordinate
        ):
            raise CrossGeometryInvariantViolation(
                "semantic support key is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_semantic_support.v1",
            "schema_version": SCHEMA_VERSION,
            "remaining_horizon": self.remaining_horizon,
            "state_coordinate": _jsonable(self.state_coordinate),
            "action_coordinate": _jsonable(self.action_coordinate),
        }

    @property
    def support_id(self) -> str:
        return _content_id("support", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_id": self.support_id}


def _support_key(
    profile: CoordinateProfileV1,
    context: CrossGraphStructuralContextV1,
    catalogue: CrossGraphStateCatalogueV1,
    action: GraphActionViewV1,
) -> SemanticSupportKeyV1:
    return SemanticSupportKeyV1(
        catalogue.state.remaining_horizon,
        _state_coordinate(profile, context, catalogue.state),
        _action_coordinate(profile, context, catalogue, action),
    )


@dataclass(frozen=True, slots=True)
class TargetSymbolicAtomV1:
    atom_index: int
    next_state: GraphStateViewV1
    next_legal_actions: tuple[GraphActionViewV1, ...]
    normalized_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        if (
            type(self.atom_index) is not int
            or not 0 <= self.atom_index < MAX_STRUCTURAL_ATOMS_PER_ROW
            or type(self.next_state) is not GraphStateViewV1
            or type(self.next_legal_actions) is not tuple
            or any(
                type(item) is not GraphActionViewV1
                for item in self.next_legal_actions
            )
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or self.failure != self.next_state.failure
            or self.terminal != self.failure
        ):
            raise CrossGeometryInvariantViolation(
                "target symbolic atom is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_symbolic_atom.v1",
            "schema_version": SCHEMA_VERSION,
            "atom_index": self.atom_index,
            "next_state": self.next_state.to_document(),
            "next_legal_actions": [
                item.to_document() for item in self.next_legal_actions
            ],
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "probability": None,
        }

    @property
    def atom_id(self) -> str:
        return _content_id("atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


def _catalogue_for_view(
    context: CrossGraphStructuralContextV1,
    state: GraphStateViewV1,
) -> CrossGraphStateCatalogueV1:
    kernel = GraphMergeKernelV1(context)
    ground = G2048State(
        state.ranks,
        G2048Status.FAILURE if state.failure else G2048Status.ACTIVE,
    )
    actions = tuple(
        GraphActionViewV1(
            state.state_id,
            action.first,
            action.second,
            action.survivor,
        )
        for action in kernel.actions(ground)
    )
    return CrossGraphStateCatalogueV1(context.context_id, state, actions)


def _symbolic_atoms(
    context: CrossGraphStructuralContextV1,
    catalogue: CrossGraphStateCatalogueV1,
    action: GraphActionViewV1,
) -> tuple[TargetSymbolicAtomV1, ...]:
    if (
        catalogue.context_id != context.context_id
        or action not in catalogue.legal_actions
    ):
        raise CrossGeometryInvariantViolation(
            "symbolic atom request is stale or foreign"
        )
    kernel = GraphMergeKernelV1(context)
    ground = G2048State(catalogue.state.ranks)
    ground_action = G2048Action(
        action.first,
        action.second,
        action.survivor,
    )
    board, _, empty_cells, reward = kernel._merged_board(
        ground,
        ground_action,
    )
    atoms: list[TargetSymbolicAtomV1] = []
    for cell in empty_cells:
        for spawn_rank in (context.low_rank, context.high_rank):
            next_board = board.copy()
            next_board[cell] = spawn_rank
            provisional = G2048State(tuple(next_board))
            failure = not kernel.actions(provisional)
            next_view = GraphStateViewV1(
                context.topology.topology_id,
                provisional.board,
                failure,
                catalogue.state.remaining_horizon - 1,
            )
            next_legal_actions = (
                ()
                if failure or next_view.remaining_horizon == 0
                else _catalogue_for_view(
                    context,
                    next_view,
                ).legal_actions
            )
            atoms.append(
                TargetSymbolicAtomV1(
                    len(atoms),
                    next_view,
                    next_legal_actions,
                    reward / HORIZON,
                    failure,
                    failure,
                )
            )
    if len(atoms) != MAX_STRUCTURAL_ATOMS_PER_ROW:
        raise CrossGeometryInvariantViolation(
            "registered four-vertex merge must have four symbolic atoms"
        )
    return tuple(atoms)


class TargetAuditOutcome(str, Enum):
    FAILED_MISSING_SUPPORT = "FAILED_MISSING_SUPPORT"
    FAILED_ACTION_AVAILABILITY = "FAILED_ACTION_AVAILABILITY"
    FAILED_RISK_OR_REGRET = "FAILED_RISK_OR_REGRET"
    CERTIFIED = "CERTIFIED"


@dataclass(frozen=True, slots=True)
class TargetModelAuditV1:
    context_id: str
    profile_id: str
    model_id: str
    scope_kind: str
    scope_ids: tuple[str, ...]
    outcome: TargetAuditOutcome
    missing_support_ids: tuple[str, ...]
    unavailable_state_keys: tuple[tuple[Any, ...], ...]
    failure_upper: Fraction
    normalized_reward_lower: Fraction
    normalized_regret_upper: Fraction
    decisions: tuple["AbstractDecisionV1", ...]
    target_transition_calls: int = 0
    source_dynamics_used: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "audit context"),
            (self.profile_id, "audit profile"),
            (self.model_id, "audit model"),
        ):
            _cid(value, field)
        if (
            self.scope_kind not in ("CONTEXT", "OCCURRENCE")
            or type(self.scope_ids) is not tuple
            or not self.scope_ids
            or type(self.outcome) is not TargetAuditOutcome
            or self.missing_support_ids
            != tuple(sorted(set(self.missing_support_ids)))
            or type(self.unavailable_state_keys) is not tuple
            or type(self.failure_upper) is not Fraction
            or not 0 <= self.failure_upper <= 1
            or type(self.normalized_reward_lower) is not Fraction
            or self.normalized_reward_lower < 0
            or type(self.normalized_regret_upper) is not Fraction
            or not 0 <= self.normalized_regret_upper <= 1
            or type(self.decisions) is not tuple
            or any(type(item) is not AbstractDecisionV1 for item in self.decisions)
            or self.target_transition_calls != 0
            or self.source_dynamics_used is not False
        ):
            raise CrossGeometryInvariantViolation("target audit is invalid")
        for value in self.scope_ids:
            _cid(value, "audit scope item")
        for value in self.missing_support_ids:
            _cid(value, "audit missing support")
        if self.outcome is TargetAuditOutcome.CERTIFIED and (
            self.failure_upper >= RISK_TOLERANCE
            or self.normalized_regret_upper > RISK_TOLERANCE
            or self.missing_support_ids
            or self.unavailable_state_keys
        ):
            raise CrossGeometryInvariantViolation(
                "certified audit violates its thresholds"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_model_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "profile_id": self.profile_id,
            "model_id": self.model_id,
            "scope_kind": self.scope_kind,
            "scope_ids": list(self.scope_ids),
            "outcome": self.outcome.value,
            "missing_support_ids": list(self.missing_support_ids),
            "unavailable_state_keys": _jsonable(
                self.unavailable_state_keys
            ),
            "failure_upper": _fdoc(self.failure_upper),
            "normalized_reward_lower": _fdoc(
                self.normalized_reward_lower
            ),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "decisions": [item.to_document() for item in self.decisions],
            "target_transition_calls": self.target_transition_calls,
            "source_dynamics_used": self.source_dynamics_used,
            "family_confidence_lower": _fdoc(FAMILY_CONFIDENCE_LOWER),
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


@dataclass(frozen=True, slots=True)
class TargetRowAuthorizationV1:
    context_id: str
    profile_id: str
    model_id: str
    failed_audit_id: str
    round_index: int
    support_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "authorization context"),
            (self.profile_id, "authorization profile"),
            (self.model_id, "authorization model"),
            (self.failed_audit_id, "authorization failed audit"),
        ):
            _cid(value, field)
        if (
            type(self.round_index) is not int
            or self.round_index not in (1, 2)
            or self.support_ids != tuple(sorted(set(self.support_ids)))
            or not self.support_ids
        ):
            raise CrossGeometryInvariantViolation(
                "target authorization is invalid"
            )
        for item in self.support_ids:
            _cid(item, "authorization support")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "profile_id": self.profile_id,
            "model_id": self.model_id,
            "failed_audit_id": self.failed_audit_id,
            "round_index": self.round_index,
            "support_ids": list(self.support_ids),
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization_id": self.authorization_id,
        }


def authorize_missing_support_v1(
    context: CrossGraphStructuralContextV1,
    profile: CoordinateProfileV1,
    model: "TargetStatisticalRAPMV1",
    audit: TargetModelAuditV1,
    round_index: int,
) -> TargetRowAuthorizationV1:
    if (
        audit.context_id != context.context_id
        or audit.profile_id != profile.profile_id
        or audit.model_id != model.model_id
        or audit.outcome is not TargetAuditOutcome.FAILED_MISSING_SUPPORT
        or not audit.missing_support_ids
        or model.context_id != context.context_id
        or model.profile_id != profile.profile_id
    ):
        raise CrossGeometryInvariantViolation(
            "only the current failed missing-support proof can authorize rows"
        )
    return TargetRowAuthorizationV1(
        context.context_id,
        profile.profile_id,
        model.model_id,
        audit.audit_id,
        round_index,
        audit.missing_support_ids,
    )


def _counter_prefix(
    context: CrossGraphStructuralContextV1,
    authorization: TargetRowAuthorizationV1,
    support: SemanticSupportKeyV1,
    catalogue: CrossGraphStateCatalogueV1,
    action: GraphActionViewV1,
) -> bytes:
    payload = {
        "schema": "acfqp.cross_geometry_counter_draw.v1",
        "context_id": context.context_id,
        "authorization_id": authorization.authorization_id,
        "support_id": support.support_id,
        "state": catalogue.state.to_document(),
        "action": action.to_document(),
        "seed": (
            f"acfqp-v0065-{context.context_key}-"
            f"round-{authorization.round_index}-v1"
        ),
    }
    return (
        b"acfqp:cross-geometry-counter-draw:v1\x00"
        + canonical_json_bytes(payload)
    )


def _counter_uint256(prefix: bytes, sample_index: int) -> int:
    return int.from_bytes(
        hashlib.sha256(
            prefix + b"\x00" + sample_index.to_bytes(8, "big")
        ).digest(),
        "big",
    )


def _pack_two_bit_indices(indices: list[int]) -> str:
    if len(indices) % 4:
        raise AssertionError("two-bit packing requires blocks of four")
    packed = bytearray(len(indices) // 4)
    for offset in range(0, len(indices), 4):
        packed[offset // 4] = (
            indices[offset]
            | (indices[offset + 1] << 2)
            | (indices[offset + 2] << 4)
            | (indices[offset + 3] << 6)
        )
    return bytes(packed).hex()


def _unpack_two_bit_indices(draws_hex: str) -> tuple[int, ...]:
    raw = bytes.fromhex(draws_hex)
    result: list[int] = []
    for value in raw:
        result.extend(
            (
                value & 3,
                (value >> 2) & 3,
                (value >> 4) & 3,
                (value >> 6) & 3,
            )
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class PackedTargetGroundRowV1:
    context_id: str
    acquisition_profile_id: str
    support: SemanticSupportKeyV1
    authorization_id: str
    round_index: int
    catalogue: CrossGraphStateCatalogueV1
    action: GraphActionViewV1
    atoms: tuple[TargetSymbolicAtomV1, ...]
    sample_count: int
    draws_hex: str

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "sampled row context"),
            (self.acquisition_profile_id, "sampled row profile"),
            (self.authorization_id, "sampled row authorization"),
        ):
            _cid(value, field)
        if (
            type(self.support) is not SemanticSupportKeyV1
            or type(self.catalogue) is not CrossGraphStateCatalogueV1
            or type(self.action) is not GraphActionViewV1
            or self.context_id != self.catalogue.context_id
            or self.action not in self.catalogue.legal_actions
            or type(self.atoms) is not tuple
            or tuple(item.atom_index for item in self.atoms)
            != tuple(range(MAX_STRUCTURAL_ATOMS_PER_ROW))
            or type(self.sample_count) is not int
            or self.sample_count != SAMPLE_COUNT_PER_GROUND_ROW
            or type(self.draws_hex) is not str
            or len(self.draws_hex) != self.sample_count // 2
            or type(self.round_index) is not int
            or self.round_index not in (1, 2)
        ):
            raise CrossGeometryInvariantViolation(
                "packed target ground row is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_sampled_ground_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "acquisition_profile_id": self.acquisition_profile_id,
            "support": self.support.to_document(),
            "authorization_id": self.authorization_id,
            "round_index": self.round_index,
            "catalogue": self.catalogue.to_document(),
            "action": self.action.to_document(),
            "atoms": [item.to_document() for item in self.atoms],
            "sample_count": self.sample_count,
            "draw_encoding": "packed_2bit_little_slot_v1",
            "draws_hex": self.draws_hex,
        }

    @property
    def sampled_row_id(self) -> str:
        return _content_id("sampled_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "sampled_row_id": self.sampled_row_id}


@dataclass(frozen=True, slots=True)
class TargetGroundEvidenceV1:
    context_id: str
    acquisition_profile_id: str
    authorization_id: str
    round_index: int
    sampled_rows: tuple[PackedTargetGroundRowV1, ...]
    source_rows_used_as_target_dynamics: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "evidence context"),
            (self.acquisition_profile_id, "evidence profile"),
            (self.authorization_id, "evidence authorization"),
        ):
            _cid(value, field)
        if (
            type(self.sampled_rows) is not tuple
            or not self.sampled_rows
            or any(
                type(item) is not PackedTargetGroundRowV1
                or item.context_id != self.context_id
                or item.acquisition_profile_id
                != self.acquisition_profile_id
                or item.authorization_id != self.authorization_id
                or item.round_index != self.round_index
                for item in self.sampled_rows
            )
            or tuple(item.sampled_row_id for item in self.sampled_rows)
            != tuple(
                sorted({item.sampled_row_id for item in self.sampled_rows})
            )
            or self.source_rows_used_as_target_dynamics != 0
        ):
            raise CrossGeometryInvariantViolation(
                "target evidence identity or ordering changed"
            )

    @property
    def ground_row_count(self) -> int:
        return len(self.sampled_rows)

    @property
    def generative_sample_count(self) -> int:
        return self.ground_row_count * SAMPLE_COUNT_PER_GROUND_ROW

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_ground_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "acquisition_profile_id": self.acquisition_profile_id,
            "authorization_id": self.authorization_id,
            "round_index": self.round_index,
            "sampled_rows": [
                item.to_document() for item in self.sampled_rows
            ],
            "ground_row_count": self.ground_row_count,
            "generative_sample_count": self.generative_sample_count,
            "source_rows_used_as_target_dynamics": (
                self.source_rows_used_as_target_dynamics
            ),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


def acquire_authorized_target_evidence_v1(
    context: CrossGraphStructuralContextV1,
    profile: CoordinateProfileV1,
    authorization: TargetRowAuthorizationV1,
    catalogues: tuple[CrossGraphStateCatalogueV1, ...],
) -> TargetGroundEvidenceV1:
    if (
        context.split is not CrossGraphSplit.TARGET
        or authorization.context_id != context.context_id
        or authorization.profile_id != profile.profile_id
        or type(catalogues) is not tuple
        or not catalogues
        or any(item.context_id != context.context_id for item in catalogues)
    ):
        raise CrossGeometryInvariantViolation(
            "target acquisition binding is invalid"
        )
    kernel = GraphMergeKernelV1(context)
    authorized = set(authorization.support_ids)
    rows: list[PackedTargetGroundRowV1] = []
    seen_supports: set[str] = set()
    for catalogue in catalogues:
        for action in catalogue.legal_actions:
            support = _support_key(profile, context, catalogue, action)
            if support.support_id not in authorized:
                continue
            atoms = _symbolic_atoms(context, catalogue, action)
            prefix = _counter_prefix(
                context,
                authorization,
                support,
                catalogue,
                action,
            )
            indices = [
                kernel.sample_structural_atom_index(
                    len(atoms) // 2,
                    _counter_uint256(prefix, sample_index),
                )
                for sample_index in range(SAMPLE_COUNT_PER_GROUND_ROW)
            ]
            rows.append(
                PackedTargetGroundRowV1(
                    context.context_id,
                    profile.profile_id,
                    support,
                    authorization.authorization_id,
                    authorization.round_index,
                    catalogue,
                    action,
                    atoms,
                    SAMPLE_COUNT_PER_GROUND_ROW,
                    _pack_two_bit_indices(indices),
                )
            )
            seen_supports.add(support.support_id)
    if seen_supports != authorized:
        raise CrossGeometryInvariantViolation(
            "authorized support was not completely materialized"
        )
    return TargetGroundEvidenceV1(
        context.context_id,
        profile.profile_id,
        authorization.authorization_id,
        authorization.round_index,
        tuple(sorted(rows, key=lambda item: item.sampled_row_id)),
    )


@dataclass(frozen=True, slots=True)
class TargetEvidenceVerificationV1:
    evidence_id: str
    context_id: str
    authorization_id: str
    replayed_row_count: int
    replayed_sample_count: int
    raw_draws_replayed: bool
    symbolic_support_replayed: bool
    verifier_kind: str = "same_implementation_semantic_replay_v1"

    def __post_init__(self) -> None:
        for value, field in (
            (self.evidence_id, "verification evidence"),
            (self.context_id, "verification context"),
            (self.authorization_id, "verification authorization"),
        ):
            _cid(value, field)
        if (
            type(self.replayed_row_count) is not int
            or self.replayed_row_count <= 0
            or self.replayed_sample_count
            != self.replayed_row_count * SAMPLE_COUNT_PER_GROUND_ROW
            or self.raw_draws_replayed is not True
            or self.symbolic_support_replayed is not True
            or self.verifier_kind
            != "same_implementation_semantic_replay_v1"
        ):
            raise CrossGeometryInvariantViolation(
                "target evidence verification is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_evidence_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "context_id": self.context_id,
            "authorization_id": self.authorization_id,
            "replayed_row_count": self.replayed_row_count,
            "replayed_sample_count": self.replayed_sample_count,
            "raw_draws_replayed": self.raw_draws_replayed,
            "symbolic_support_replayed": self.symbolic_support_replayed,
            "verifier_kind": self.verifier_kind,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("evidence_verification", self._payload())


def verify_target_evidence_v1(
    context: CrossGraphStructuralContextV1,
    profile: CoordinateProfileV1,
    authorization: TargetRowAuthorizationV1,
    catalogues: tuple[CrossGraphStateCatalogueV1, ...],
    evidence: TargetGroundEvidenceV1,
) -> TargetEvidenceVerificationV1:
    expected = acquire_authorized_target_evidence_v1(
        context,
        profile,
        authorization,
        catalogues,
    )
    if evidence.to_document() != expected.to_document():
        raise CrossGeometryInvariantViolation(
            "target evidence failed raw-draw semantic replay"
        )
    return TargetEvidenceVerificationV1(
        evidence.evidence_id,
        context.context_id,
        authorization.authorization_id,
        evidence.ground_row_count,
        evidence.generative_sample_count,
        True,
        True,
    )


@dataclass(frozen=True, slots=True)
class TargetDestinationIntervalV1:
    destination: Destination
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.destination) is not tuple
            or not self.destination
            or self.destination[0] not in (
                "FAILURE",
                "SAFE_TERMINAL",
                "ACTIVE",
            )
            or type(self.lower) is not Fraction
            or type(self.upper) is not Fraction
            or not 0 <= self.lower <= self.upper <= 1
        ):
            raise CrossGeometryInvariantViolation(
                "target destination interval is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_destination_interval.v1",
            "schema_version": SCHEMA_VERSION,
            "destination": _jsonable(self.destination),
            "lower": _fdoc(self.lower),
            "upper": _fdoc(self.upper),
        }

    @property
    def interval_id(self) -> str:
        return _content_id("interval", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "interval_id": self.interval_id}


@dataclass(frozen=True, slots=True)
class TargetModelRowV1:
    support: SemanticSupportKeyV1
    intervals: tuple[TargetDestinationIntervalV1, ...]
    member_ground_row_ids: tuple[str, ...]
    normalized_reward: Fraction
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.support) is not SemanticSupportKeyV1
            or type(self.intervals) is not tuple
            or not self.intervals
            or any(
                type(item) is not TargetDestinationIntervalV1
                for item in self.intervals
            )
            or tuple(item.destination for item in self.intervals)
            != tuple(
                sorted(
                    {item.destination for item in self.intervals},
                    key=repr,
                )
            )
            or sum(
                (item.lower for item in self.intervals),
                Fraction(0),
            )
            > 1
            or sum(
                (item.upper for item in self.intervals),
                Fraction(0),
            )
            < 1
            or self.member_ground_row_ids
            != tuple(sorted(set(self.member_ground_row_ids)))
            or not self.member_ground_row_ids
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or self.evidence_ids != tuple(sorted(set(self.evidence_ids)))
            or not self.evidence_ids
        ):
            raise CrossGeometryInvariantViolation("target model row is invalid")
        for value in self.member_ground_row_ids:
            _cid(value, "model member row")
        for value in self.evidence_ids:
            _cid(value, "model evidence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_model_row.v1",
            "schema_version": SCHEMA_VERSION,
            "support": self.support.to_document(),
            "intervals": [item.to_document() for item in self.intervals],
            "member_ground_row_ids": list(self.member_ground_row_ids),
            "normalized_reward": _fdoc(self.normalized_reward),
            "evidence_ids": list(self.evidence_ids),
        }

    @property
    def model_row_id(self) -> str:
        return _content_id("model_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_row_id": self.model_row_id}


@dataclass(frozen=True, slots=True)
class TargetStatisticalRAPMV1:
    context_id: str
    structural_id: str
    proposal_id: str
    profile_id: str
    epoch_index: int
    rows: tuple[TargetModelRowV1, ...]
    evidence_ids: tuple[str, ...]
    source_dynamics_imported: bool = False
    exact_probabilities_used: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "model context"),
            (self.structural_id, "model structural"),
            (self.proposal_id, "model proposal"),
            (self.profile_id, "model profile"),
        ):
            _cid(value, field)
        if (
            type(self.epoch_index) is not int
            or not 0 <= self.epoch_index <= 3
            or type(self.rows) is not tuple
            or tuple(item.support.support_id for item in self.rows)
            != tuple(sorted({item.support.support_id for item in self.rows}))
            or self.evidence_ids != tuple(sorted(set(self.evidence_ids)))
            or self.source_dynamics_imported is not False
            or self.exact_probabilities_used is not False
        ):
            raise CrossGeometryInvariantViolation(
                "target RAPM identity or authority changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_statistical_rapm.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "structural_id": self.structural_id,
            "proposal_id": self.proposal_id,
            "profile_id": self.profile_id,
            "epoch_index": self.epoch_index,
            "rows": [item.to_document() for item in self.rows],
            "evidence_ids": list(self.evidence_ids),
            "source_dynamics_imported": self.source_dynamics_imported,
            "exact_probabilities_used": self.exact_probabilities_used,
        }

    @property
    def model_id(self) -> str:
        return _content_id("model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}


def empty_target_rapm_v1(
    context: CrossGraphStructuralContextV1,
    proposal: RelationalGraphCoordinateProposalV1,
    profile: CoordinateProfileV1,
) -> TargetStatisticalRAPMV1:
    return TargetStatisticalRAPMV1(
        context.context_id,
        context.structural_id,
        proposal.proposal_id,
        profile.profile_id,
        0,
        (),
        (),
    )


def _atom_destination(
    profile: CoordinateProfileV1,
    context: CrossGraphStructuralContextV1,
    atom: TargetSymbolicAtomV1,
) -> Destination:
    if atom.failure:
        return ("FAILURE",)
    if atom.next_state.remaining_horizon == 0:
        return ("SAFE_TERMINAL",)
    return (
        "ACTIVE",
        atom.next_state.remaining_horizon,
        _state_coordinate(profile, context, atom.next_state),
    )


def build_target_statistical_rapm_v1(
    context: CrossGraphStructuralContextV1,
    proposal: RelationalGraphCoordinateProposalV1,
    profile: CoordinateProfileV1,
    evidences: tuple[TargetGroundEvidenceV1, ...],
    verifications: tuple[TargetEvidenceVerificationV1, ...],
) -> TargetStatisticalRAPMV1:
    if (
        type(evidences) is not tuple
        or type(verifications) is not tuple
        or len(evidences) not in (1, 2)
        or len(evidences) != len(verifications)
        or tuple(item.evidence_id for item in evidences)
        != tuple(item.evidence_id for item in verifications)
        or any(item.context_id != context.context_id for item in evidences)
        or any(
            item.context_id != context.context_id for item in verifications
        )
    ):
        raise CrossGeometryInvariantViolation(
            "target model evidence chain is invalid"
        )
    groups: dict[str, tuple[SemanticSupportKeyV1, list[PackedTargetGroundRowV1]]] = {}
    evidence_by_row: dict[str, str] = {}
    for evidence in evidences:
        for sampled in evidence.sampled_rows:
            support = _support_key(
                profile,
                context,
                sampled.catalogue,
                sampled.action,
            )
            prior = groups.get(support.support_id)
            if prior is None:
                groups[support.support_id] = (support, [sampled])
            else:
                prior[1].append(sampled)
            evidence_by_row[sampled.sampled_row_id] = evidence.evidence_id
    model_rows: list[TargetModelRowV1] = []
    for support_id in sorted(groups):
        support, members = groups[support_id]
        member_bounds: list[
            dict[Destination, tuple[Fraction, Fraction]]
        ] = []
        all_destinations: set[Destination] = set()
        rewards: set[Fraction] = set()
        for member in members:
            destinations = tuple(
                _atom_destination(profile, context, atom)
                for atom in member.atoms
            )
            structural_destinations = set(destinations)
            counts: dict[Destination, int] = {}
            for atom_index in _unpack_two_bit_indices(member.draws_hex):
                destination = destinations[atom_index]
                counts[destination] = counts.get(destination, 0) + 1
            bounds: dict[Destination, tuple[Fraction, Fraction]] = {}
            for destination in structural_destinations:
                empirical = Fraction(
                    counts.get(destination, 0),
                    SAMPLE_COUNT_PER_GROUND_ROW,
                )
                bounds[destination] = (
                    max(Fraction(0), empirical - HOEFFDING_RADIUS),
                    min(Fraction(1), empirical + HOEFFDING_RADIUS),
                )
            member_bounds.append(bounds)
            all_destinations.update(structural_destinations)
            rewards.update(item.normalized_reward for item in member.atoms)
        if len(rewards) != 1:
            raise CrossGeometryInvariantViolation(
                "one semantic support has inconsistent merge rewards"
            )
        intervals = tuple(
            TargetDestinationIntervalV1(
                destination,
                min(
                    item.get(
                        destination,
                        (Fraction(0), Fraction(0)),
                    )[0]
                    for item in member_bounds
                ),
                max(
                    item.get(
                        destination,
                        (Fraction(0), Fraction(0)),
                    )[1]
                    for item in member_bounds
                ),
            )
            for destination in sorted(all_destinations, key=repr)
        )
        model_rows.append(
            TargetModelRowV1(
                support,
                intervals,
                tuple(
                    sorted(item.sampled_row_id for item in members)
                ),
                next(iter(rewards)),
                tuple(
                    sorted(
                        {
                            evidence_by_row[item.sampled_row_id]
                            for item in members
                        }
                    )
                ),
            )
        )
    return TargetStatisticalRAPMV1(
        context.context_id,
        context.structural_id,
        proposal.proposal_id,
        profile.profile_id,
        len(evidences) + profile.refinement_index,
        tuple(model_rows),
        tuple(sorted(item.evidence_id for item in evidences)),
    )


def _interval_expectation(
    intervals: tuple[TargetDestinationIntervalV1, ...],
    values: Mapping[Destination, Fraction],
    *,
    maximize: bool,
) -> Fraction:
    probabilities = {item.destination: item.lower for item in intervals}
    residual = 1 - sum(probabilities.values(), Fraction(0))
    ordered = sorted(
        intervals,
        key=lambda item: (
            -values[item.destination] if maximize else values[item.destination],
            repr(item.destination),
        ),
    )
    for item in ordered:
        addition = min(
            item.upper - probabilities[item.destination],
            residual,
        )
        probabilities[item.destination] += addition
        residual -= addition
        if residual == 0:
            break
    if residual:
        raise CrossGeometryInvariantViolation(
            "interval upper bounds do not cover one simplex"
        )
    return sum(
        probabilities[destination] * values[destination]
        for destination in probabilities
    )


@dataclass(frozen=True, slots=True)
class AbstractDecisionV1:
    remaining_horizon: int
    state_coordinate: StateCoordinate
    action_coordinate: ActionCoordinate
    failure_upper: Fraction
    reward_lower: Fraction
    reward_upper: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, HORIZON)
            or type(self.state_coordinate) is not tuple
            or type(self.action_coordinate) is not tuple
            or any(
                type(item) is not Fraction
                for item in (
                    self.failure_upper,
                    self.reward_lower,
                    self.reward_upper,
                )
            )
            or not 0 <= self.failure_upper <= 1
            or not 0 <= self.reward_lower <= self.reward_upper <= 1
        ):
            raise CrossGeometryInvariantViolation(
                "abstract decision is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_abstract_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "remaining_horizon": self.remaining_horizon,
            "state_coordinate": _jsonable(self.state_coordinate),
            "action_coordinate": _jsonable(self.action_coordinate),
            "failure_upper": _fdoc(self.failure_upper),
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
        }

    @property
    def decision_id(self) -> str:
        return _content_id("decision", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


def audit_target_rapm_v1(
    context: CrossGraphStructuralContextV1,
    profile: CoordinateProfileV1,
    model: TargetStatisticalRAPMV1,
    catalogues: tuple[CrossGraphStateCatalogueV1, ...],
    *,
    scope_kind: str = "CONTEXT",
) -> TargetModelAuditV1:
    if (
        model.context_id != context.context_id
        or model.structural_id != context.structural_id
        or model.profile_id != profile.profile_id
        or type(catalogues) is not tuple
        or not catalogues
        or any(item.context_id != context.context_id for item in catalogues)
        or scope_kind not in ("CONTEXT", "OCCURRENCE")
    ):
        raise CrossGeometryInvariantViolation(
            "model-only target audit binding is invalid"
        )
    model_by_support = {
        item.support.support_id: item for item in model.rows
    }
    missing = {
        _support_key(profile, context, catalogue, action).support_id
        for catalogue in catalogues
        for action in catalogue.legal_actions
        if _support_key(
            profile,
            context,
            catalogue,
            action,
        ).support_id not in model_by_support
    }
    if missing:
        return TargetModelAuditV1(
            context.context_id,
            profile.profile_id,
            model.model_id,
            scope_kind,
            tuple(item.catalogue_id for item in catalogues),
            TargetAuditOutcome.FAILED_MISSING_SUPPORT,
            tuple(sorted(missing)),
            (),
            Fraction(1),
            Fraction(0),
            Fraction(1),
            (),
        )

    members_by_state: dict[
        tuple[int, StateCoordinate],
        list[CrossGraphStateCatalogueV1],
    ] = {}
    for catalogue in catalogues:
        key = (
            catalogue.state.remaining_horizon,
            _state_coordinate(profile, context, catalogue.state),
        )
        members_by_state.setdefault(key, []).append(catalogue)
    unavailable: list[tuple[Any, ...]] = []
    common_actions: dict[
        tuple[int, StateCoordinate],
        tuple[ActionCoordinate, ...],
    ] = {}
    for key, members in members_by_state.items():
        sets = [
            {
                _action_coordinate(
                    profile,
                    context,
                    catalogue,
                    action,
                )
                for action in catalogue.legal_actions
            }
            for catalogue in members
        ]
        intersection = set.intersection(*sets)
        if not intersection:
            unavailable.append(key)
        common_actions[key] = tuple(sorted(intersection, key=repr))
    if unavailable:
        return TargetModelAuditV1(
            context.context_id,
            profile.profile_id,
            model.model_id,
            scope_kind,
            tuple(item.catalogue_id for item in catalogues),
            TargetAuditOutcome.FAILED_ACTION_AVAILABILITY,
            (),
            tuple(sorted(unavailable, key=repr)),
            Fraction(1),
            Fraction(0),
            Fraction(1),
            (),
        )

    decision_by_state: dict[
        tuple[int, StateCoordinate],
        AbstractDecisionV1,
    ] = {}
    optimistic_reward_by_state: dict[
        tuple[int, StateCoordinate],
        Fraction,
    ] = {}
    for remaining in (1, HORIZON):
        state_keys = sorted(
            (
                key
                for key in members_by_state
                if key[0] == remaining
            ),
            key=repr,
        )
        for key in state_keys:
            candidates: list[AbstractDecisionV1] = []
            for action_coordinate in common_actions[key]:
                support = SemanticSupportKeyV1(
                    remaining,
                    key[1],
                    action_coordinate,
                )
                row = model_by_support[support.support_id]
                failure_values: dict[Destination, Fraction] = {}
                reward_lower_values: dict[Destination, Fraction] = {}
                reward_upper_values: dict[Destination, Fraction] = {}
                for interval in row.intervals:
                    destination = interval.destination
                    if destination[0] == "FAILURE":
                        failure_values[destination] = Fraction(1)
                        reward_lower_values[destination] = Fraction(0)
                        reward_upper_values[destination] = Fraction(0)
                    elif destination[0] == "SAFE_TERMINAL":
                        failure_values[destination] = Fraction(0)
                        reward_lower_values[destination] = Fraction(0)
                        reward_upper_values[destination] = Fraction(0)
                    else:
                        successor_key = (destination[1], destination[2])
                        successor = decision_by_state[successor_key]
                        failure_values[destination] = successor.failure_upper
                        reward_lower_values[destination] = successor.reward_lower
                        reward_upper_values[destination] = (
                            optimistic_reward_by_state[successor_key]
                        )
                failure_upper = _interval_expectation(
                    row.intervals,
                    failure_values,
                    maximize=True,
                )
                reward_lower = row.normalized_reward + _interval_expectation(
                    row.intervals,
                    reward_lower_values,
                    maximize=False,
                )
                reward_upper = row.normalized_reward + _interval_expectation(
                    row.intervals,
                    reward_upper_values,
                    maximize=True,
                )
                candidates.append(
                    AbstractDecisionV1(
                        remaining,
                        key[1],
                        action_coordinate,
                        failure_upper,
                        reward_lower,
                        reward_upper,
                    )
                )
            selected = min(
                candidates,
                key=lambda item: (
                    item.failure_upper,
                    -item.reward_lower,
                    repr(item.action_coordinate),
                ),
            )
            decision_by_state[key] = selected
            optimistic_reward_by_state[key] = max(
                item.reward_upper for item in candidates
            )

    root_keys = {
        (
            HORIZON,
            _state_coordinate(profile, context, item.state),
        )
        for item in catalogues
        if item.state.remaining_horizon == HORIZON
    }
    if not root_keys:
        raise CrossGeometryInvariantViolation(
            "audit scope contains no root state"
        )
    failure_upper = max(
        decision_by_state[item].failure_upper for item in root_keys
    )
    reward_lower = min(
        decision_by_state[item].reward_lower for item in root_keys
    )
    regret_upper = max(
        optimistic_reward_by_state[item]
        - decision_by_state[item].reward_lower
        for item in root_keys
    )
    outcome = (
        TargetAuditOutcome.CERTIFIED
        if failure_upper < RISK_TOLERANCE
        and regret_upper <= RISK_TOLERANCE
        else TargetAuditOutcome.FAILED_RISK_OR_REGRET
    )
    return TargetModelAuditV1(
        context.context_id,
        profile.profile_id,
        model.model_id,
        scope_kind,
        tuple(item.catalogue_id for item in catalogues),
        outcome,
        (),
        (),
        failure_upper,
        reward_lower,
        regret_upper,
        tuple(
            sorted(
                decision_by_state.values(),
                key=lambda item: item.decision_id,
            )
        ),
    )


@dataclass(frozen=True, slots=True)
class CoordinateRefinementCandidateV1:
    profile: CoordinateProfileV1
    model_id: str
    audit_id: str
    outcome: TargetAuditOutcome
    added_node_count: int
    abstract_support_count: int

    def to_document(self) -> dict[str, Any]:
        return {
            "profile": self.profile.to_document(),
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "outcome": self.outcome.value,
            "added_node_count": self.added_node_count,
            "abstract_support_count": self.abstract_support_count,
        }


@dataclass(frozen=True, slots=True)
class CoordinateRefinementTraceV1:
    context_id: str
    failed_base_audit_id: str
    candidate_registry_id: str
    candidates: tuple[CoordinateRefinementCandidateV1, ...]
    selected_profile_id: str
    target_program_generation_count: int = 0
    target_primitive_generation_count: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "refinement context"),
            (self.failed_base_audit_id, "refinement failed audit"),
            (self.candidate_registry_id, "refinement registry"),
            (self.selected_profile_id, "refinement selected profile"),
        ):
            _cid(value, field)
        if (
            type(self.candidates) is not tuple
            or not self.candidates
            or self.selected_profile_id
            not in {item.profile.profile_id for item in self.candidates}
            or self.target_program_generation_count != 0
            or self.target_primitive_generation_count != 0
        ):
            raise CrossGeometryInvariantViolation(
                "coordinate refinement trace is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_refinement_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "failed_base_audit_id": self.failed_base_audit_id,
            "candidate_registry_id": self.candidate_registry_id,
            "candidates": [item.to_document() for item in self.candidates],
            "selected_profile_id": self.selected_profile_id,
            "target_program_generation_count": (
                self.target_program_generation_count
            ),
            "target_primitive_generation_count": (
                self.target_primitive_generation_count
            ),
        }

    @property
    def trace_id(self) -> str:
        return _content_id("refinement", self._payload())


def refine_failed_coordinate_profile_v1(
    context: CrossGraphStructuralContextV1,
    proposal: RelationalGraphCoordinateProposalV1,
    registry: GraphProgramRegistryV1,
    base_profile: CoordinateProfileV1,
    failed_audit: TargetModelAuditV1,
    evidences: tuple[TargetGroundEvidenceV1, ...],
    verifications: tuple[TargetEvidenceVerificationV1, ...],
    catalogues: tuple[CrossGraphStateCatalogueV1, ...],
) -> tuple[
    CoordinateProfileV1,
    TargetStatisticalRAPMV1,
    TargetModelAuditV1,
    CoordinateRefinementTraceV1,
]:
    if (
        failed_audit.context_id != context.context_id
        or failed_audit.profile_id != base_profile.profile_id
        or failed_audit.outcome
        not in (
            TargetAuditOutcome.FAILED_ACTION_AVAILABILITY,
            TargetAuditOutcome.FAILED_RISK_OR_REGRET,
        )
    ):
        raise CrossGeometryInvariantViolation(
            "coordinate refinement requires a current failed proof"
        )
    state_extras = tuple(
        item
        for item in registry.programs
        if item.context is GraphProgramContext.STATE
        and item.result_type is GraphProgramType.SIGNATURE
    )
    action_extras = tuple(
        item
        for item in registry.programs
        if item.context is GraphProgramContext.STATE_ACTION
        and item.result_type is GraphProgramType.INTEGER
        and item.program_id
        not in {item.program_id for item in base_profile.action_programs}
    )
    candidates: list[
        tuple[
            CoordinateRefinementCandidateV1,
            TargetStatisticalRAPMV1,
            TargetModelAuditV1,
        ]
    ] = []
    for state_extra, action_extra in product(
        state_extras,
        action_extras,
    ):
        profile = CoordinateProfileV1(
            proposal.proposal_id,
            registry.registry_id,
            base_profile.state_programs + (state_extra,),
            base_profile.action_programs + (action_extra,),
            1,
            failed_audit.audit_id,
        )
        model = build_target_statistical_rapm_v1(
            context,
            proposal,
            profile,
            evidences,
            verifications,
        )
        audit = audit_target_rapm_v1(
            context,
            profile,
            model,
            catalogues,
        )
        summary = CoordinateRefinementCandidateV1(
            profile,
            model.model_id,
            audit.audit_id,
            audit.outcome,
            state_extra.node_count + action_extra.node_count,
            len(model.rows),
        )
        candidates.append((summary, model, audit))
    certified = tuple(
        item
        for item in candidates
        if item[2].outcome is TargetAuditOutcome.CERTIFIED
    )
    if not certified:
        raise CrossGeometryInvariantViolation(
            "source-frozen refinement registry has no sound cover"
        )
    selected = min(
        certified,
        key=lambda item: (
            item[0].added_node_count,
            item[0].abstract_support_count,
            item[0].profile.state_programs[-1].program_id,
            item[0].profile.action_programs[-1].program_id,
        ),
    )
    trace = CoordinateRefinementTraceV1(
        context.context_id,
        failed_audit.audit_id,
        registry.registry_id,
        tuple(
            sorted(
                (item[0] for item in candidates),
                key=lambda item: item.profile.profile_id,
            )
        ),
        selected[0].profile.profile_id,
    )
    return selected[0].profile, selected[1], selected[2], trace


def _base_profile(
    proposal: RelationalGraphCoordinateProposalV1,
    registry: GraphProgramRegistryV1,
) -> CoordinateProfileV1:
    return CoordinateProfileV1(
        proposal.proposal_id,
        registry.registry_id,
        (proposal.state_program,),
        (proposal.action_program,),
        0,
        None,
    )


def _successor_catalogues(
    context: CrossGraphStructuralContextV1,
    evidence: TargetGroundEvidenceV1,
) -> tuple[CrossGraphStateCatalogueV1, ...]:
    states = tuple(
        G2048State(atom.next_state.ranks)
        for row in evidence.sampled_rows
        for atom in row.atoms
        if not atom.failure
        and atom.next_state.remaining_horizon == 1
    )
    return continuation_catalogues_from_states_v1(context, states)


@dataclass(frozen=True, slots=True)
class TargetOccurrenceV1:
    ordinal: int
    context_id: str
    catalogue_id: str
    initial_board: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal not in (0, 1)
            or _cid(self.context_id, "occurrence context") != self.context_id
            or _cid(self.catalogue_id, "occurrence catalogue")
            != self.catalogue_id
            or type(self.initial_board) is not tuple
            or len(self.initial_board) != 4
        ):
            raise CrossGeometryInvariantViolation("occurrence is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue_id,
            "initial_board": list(self.initial_board),
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


@dataclass(frozen=True, slots=True)
class TargetContextResultV1:
    context: CrossGraphStructuralContextV1
    base_profile: CoordinateProfileV1
    final_profile: CoordinateProfileV1
    empty_model: TargetStatisticalRAPMV1
    first_audit: TargetModelAuditV1
    first_authorization: TargetRowAuthorizationV1
    first_evidence: TargetGroundEvidenceV1
    first_verification: TargetEvidenceVerificationV1
    second_audit: TargetModelAuditV1
    second_authorization: TargetRowAuthorizationV1
    second_evidence: TargetGroundEvidenceV1
    second_verification: TargetEvidenceVerificationV1
    base_final_model: TargetStatisticalRAPMV1
    base_final_audit: TargetModelAuditV1
    refinement_trace: CoordinateRefinementTraceV1 | None
    final_model: TargetStatisticalRAPMV1
    final_audit: TargetModelAuditV1
    occurrences: tuple[TargetOccurrenceV1, ...]
    occurrence_audits: tuple[TargetModelAuditV1, ...]
    direct_controls: tuple[ColdExactH2ControlV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.context) is not CrossGraphStructuralContextV1
            or self.context.split is not CrossGraphSplit.TARGET
            or self.first_audit.outcome
            is not TargetAuditOutcome.FAILED_MISSING_SUPPORT
            or self.second_audit.outcome
            is not TargetAuditOutcome.FAILED_MISSING_SUPPORT
            or self.final_audit.outcome is not TargetAuditOutcome.CERTIFIED
            or self.final_model.context_id != self.context.context_id
            or self.final_profile.profile_id != self.final_model.profile_id
            or type(self.occurrences) is not tuple
            or len(self.occurrences) != 2
            or type(self.occurrence_audits) is not tuple
            or len(self.occurrence_audits) != 2
            or any(
                item.outcome is not TargetAuditOutcome.CERTIFIED
                for item in self.occurrence_audits
            )
            or type(self.direct_controls) is not tuple
            or len(self.direct_controls) != 2
            or any(not item.feasible for item in self.direct_controls)
        ):
            raise CrossGeometryInvariantViolation(
                "target context result is incomplete"
            )

    @property
    def context_build_ground_rows(self) -> int:
        return (
            self.first_evidence.ground_row_count
            + self.second_evidence.ground_row_count
        )

    @property
    def context_build_samples(self) -> int:
        return (
            self.first_evidence.generative_sample_count
            + self.second_evidence.generative_sample_count
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_target_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "base_profile": self.base_profile.to_document(),
            "final_profile": self.final_profile.to_document(),
            "empty_model": self.empty_model.to_document(),
            "first_audit": self.first_audit.to_document(),
            "first_authorization": self.first_authorization.to_document(),
            "first_evidence": self.first_evidence.to_document(),
            "first_verification_id": (
                self.first_verification.verification_id
            ),
            "second_audit": self.second_audit.to_document(),
            "second_authorization": self.second_authorization.to_document(),
            "second_evidence": self.second_evidence.to_document(),
            "second_verification_id": (
                self.second_verification.verification_id
            ),
            "base_final_model": self.base_final_model.to_document(),
            "base_final_audit": self.base_final_audit.to_document(),
            "refinement_trace": (
                None
                if self.refinement_trace is None
                else {
                    **self.refinement_trace._payload(),
                    "trace_id": self.refinement_trace.trace_id,
                }
            ),
            "final_model": self.final_model.to_document(),
            "final_audit": self.final_audit.to_document(),
            "occurrences": [item.to_document() for item in self.occurrences],
            "occurrence_audits": [
                item.to_document() for item in self.occurrence_audits
            ],
            "direct_controls": [
                item.to_document() for item in self.direct_controls
            ],
            "context_build_ground_rows": self.context_build_ground_rows,
            "context_build_samples": self.context_build_samples,
            "occurrence_new_ground_rows": [0, 0],
        }

    @property
    def result_id(self) -> str:
        return _content_id("target_result", self._payload())


def _run_target_context(
    context: CrossGraphStructuralContextV1,
    proposal: RelationalGraphCoordinateProposalV1,
    registry: GraphProgramRegistryV1,
) -> TargetContextResultV1:
    base_profile = _base_profile(proposal, registry)
    roots = target_root_catalogues_v1(context)
    empty_model = empty_target_rapm_v1(context, proposal, base_profile)
    first_audit = audit_target_rapm_v1(
        context,
        base_profile,
        empty_model,
        roots,
    )
    first_authorization = authorize_missing_support_v1(
        context,
        base_profile,
        empty_model,
        first_audit,
        1,
    )
    first_evidence = acquire_authorized_target_evidence_v1(
        context,
        base_profile,
        first_authorization,
        roots,
    )
    first_verification = verify_target_evidence_v1(
        context,
        base_profile,
        first_authorization,
        roots,
        first_evidence,
    )
    root_model = build_target_statistical_rapm_v1(
        context,
        proposal,
        base_profile,
        (first_evidence,),
        (first_verification,),
    )
    continuations = _successor_catalogues(context, first_evidence)
    all_catalogues = roots + continuations
    second_audit = audit_target_rapm_v1(
        context,
        base_profile,
        root_model,
        all_catalogues,
    )
    second_authorization = authorize_missing_support_v1(
        context,
        base_profile,
        root_model,
        second_audit,
        2,
    )
    second_evidence = acquire_authorized_target_evidence_v1(
        context,
        base_profile,
        second_authorization,
        continuations,
    )
    second_verification = verify_target_evidence_v1(
        context,
        base_profile,
        second_authorization,
        continuations,
        second_evidence,
    )
    evidences = (first_evidence, second_evidence)
    verifications = (first_verification, second_verification)
    base_final_model = build_target_statistical_rapm_v1(
        context,
        proposal,
        base_profile,
        evidences,
        verifications,
    )
    base_final_audit = audit_target_rapm_v1(
        context,
        base_profile,
        base_final_model,
        all_catalogues,
    )
    if base_final_audit.outcome is TargetAuditOutcome.CERTIFIED:
        final_profile = base_profile
        final_model = base_final_model
        final_audit = base_final_audit
        refinement_trace = None
    else:
        (
            final_profile,
            final_model,
            final_audit,
            refinement_trace,
        ) = refine_failed_coordinate_profile_v1(
            context,
            proposal,
            registry,
            base_profile,
            base_final_audit,
            evidences,
            verifications,
            all_catalogues,
        )
    selected_catalogues = tuple(sorted(roots, key=lambda item: item.catalogue_id)[:2])
    occurrences = tuple(
        TargetOccurrenceV1(
            ordinal,
            context.context_id,
            catalogue.catalogue_id,
            catalogue.state.ranks,
        )
        for ordinal, catalogue in enumerate(selected_catalogues)
    )
    occurrence_audits = tuple(
        audit_target_rapm_v1(
            context,
            final_profile,
            final_model,
            (catalogue,) + continuations,
            scope_kind="OCCURRENCE",
        )
        for catalogue in selected_catalogues
    )
    root_order = {
        state.board: index
        for index, state in enumerate(
            sorted(
                (
                    G2048State(item.state.ranks)
                    for item in target_root_catalogues_v1(context)
                ),
                key=lambda item: (item.board, item.status.value),
            )
        )
    }
    direct_controls = tuple(
        cold_exact_h2_oracle_v1(
            context,
            root_order[catalogue.state.ranks],
        )
        for catalogue in selected_catalogues
    )
    return TargetContextResultV1(
        context,
        base_profile,
        final_profile,
        empty_model,
        first_audit,
        first_authorization,
        first_evidence,
        first_verification,
        second_audit,
        second_authorization,
        second_evidence,
        second_verification,
        base_final_model,
        base_final_audit,
        refinement_trace,
        final_model,
        final_audit,
        occurrences,
        occurrence_audits,
        direct_controls,
    )


@dataclass(frozen=True, slots=True)
class CrossGeometryCalibrationV1:
    sample_count_per_ground_row: int
    radius: Fraction
    exponent: Fraction
    taylor_degree: int
    taylor_lower: Fraction
    per_atom_tail_upper: Fraction
    preregistered_atom_obligations: int
    family_tail_upper: Fraction
    family_confidence_lower: Fraction

    def __post_init__(self) -> None:
        if (
            self.sample_count_per_ground_row
            != SAMPLE_COUNT_PER_GROUND_ROW
            or self.radius != HOEFFDING_RADIUS
            or self.exponent
            != 2 * self.sample_count_per_ground_row * self.radius**2
            or self.taylor_degree != 19
            or self.taylor_lower <= 50_000
            or self.per_atom_tail_upper != PER_ATOM_TAIL_UPPER
            or self.preregistered_atom_obligations
            != PREREGISTERED_ATOM_OBLIGATIONS
            or self.family_tail_upper != FAMILY_TAIL_UPPER
            or self.family_confidence_lower != FAMILY_CONFIDENCE_LOWER
            or self.family_confidence_lower < Fraction(19, 20)
        ):
            raise CrossGeometryInvariantViolation(
                "cross-geometry calibration is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_calibration.v1",
            "schema_version": SCHEMA_VERSION,
            "sample_count_per_ground_row": self.sample_count_per_ground_row,
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
        }

    @property
    def calibration_id(self) -> str:
        return _content_id("calibration", self._payload())


def cross_geometry_calibration_v1() -> CrossGeometryCalibrationV1:
    exponent = (
        2 * SAMPLE_COUNT_PER_GROUND_ROW * HOEFFDING_RADIUS**2
    )
    term = Fraction(1)
    total = Fraction(1)
    for degree in range(1, 20):
        term *= exponent / degree
        total += term
    return CrossGeometryCalibrationV1(
        SAMPLE_COUNT_PER_GROUND_ROW,
        HOEFFDING_RADIUS,
        exponent,
        19,
        total,
        PER_ATOM_TAIL_UPPER,
        PREREGISTERED_ATOM_OBLIGATIONS,
        FAMILY_TAIL_UPPER,
        FAMILY_CONFIDENCE_LOWER,
    )


@dataclass(frozen=True, slots=True)
class LegacyFixedScheduleControlV1:
    context_outcomes: tuple[tuple[str, str], ...]
    abstract_certificate_count: int
    rejected_context_count: int
    false_certificate_count: int
    fixed_schedule_reused_as_target_plan: bool

    def __post_init__(self) -> None:
        if (
            self.context_outcomes
            != (
                ("c4", "CERTIFIED"),
                ("diamond", "FAILED_RISK_OR_ALIAS"),
                ("k4", "FAILED_ACTION_UNAVAILABLE"),
            )
            or self.abstract_certificate_count != 1
            or self.rejected_context_count != 2
            or self.false_certificate_count != 0
            or self.fixed_schedule_reused_as_target_plan is not False
        ):
            raise CrossGeometryInvariantViolation(
                "legacy fixed-schedule control changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_legacy_fixed_schedule_control.v1",
            "schema_version": SCHEMA_VERSION,
            "context_outcomes": [
                {"graph_key": key, "outcome": outcome}
                for key, outcome in self.context_outcomes
            ],
            "abstract_certificate_count": self.abstract_certificate_count,
            "rejected_context_count": self.rejected_context_count,
            "false_certificate_count": self.false_certificate_count,
            "fixed_schedule_reused_as_target_plan": (
                self.fixed_schedule_reused_as_target_plan
            ),
        }

    @property
    def control_id(self) -> str:
        return _content_id("legacy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "control_id": self.control_id}


@dataclass(frozen=True, slots=True)
class NoTransferControlV1:
    context_id: str
    occurrence_id: str
    source_proposal_available: bool
    target_transition_driven_abstraction_search_allowed: bool
    abstract_certificate_count: int
    direct_fallback_control_id: str
    direct_fallback_failure_probability: Fraction
    same_result_as_registered_cold_control: bool

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "no-transfer context"),
            (self.occurrence_id, "no-transfer occurrence"),
            (self.direct_fallback_control_id, "no-transfer fallback"),
        ):
            _cid(value, field)
        if (
            self.source_proposal_available is not False
            or self.target_transition_driven_abstraction_search_allowed
            is not False
            or self.abstract_certificate_count != 0
            or type(self.direct_fallback_failure_probability) is not Fraction
            or self.direct_fallback_failure_probability != Fraction(99, 5000)
            or self.same_result_as_registered_cold_control is not True
        ):
            raise CrossGeometryInvariantViolation(
                "no-transfer control must route to matched direct ground"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_no_transfer_control.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "occurrence_id": self.occurrence_id,
            "source_proposal_available": self.source_proposal_available,
            "target_transition_driven_abstraction_search_allowed": (
                self.target_transition_driven_abstraction_search_allowed
            ),
            "abstract_certificate_count": self.abstract_certificate_count,
            "direct_fallback_control_id": self.direct_fallback_control_id,
            "direct_fallback_failure_probability": _fdoc(
                self.direct_fallback_failure_probability
            ),
            "same_result_as_registered_cold_control": (
                self.same_result_as_registered_cold_control
            ),
        }

    @property
    def control_id(self) -> str:
        return _content_id("no_transfer", self._payload())


def _flip_hidden_colour_draws(
    sampled: PackedTargetGroundRowV1,
) -> PackedTargetGroundRowV1:
    indices = list(_unpack_two_bit_indices(sampled.draws_hex))
    if sampled.action.survivor != 0:
        indices = [item ^ 1 for item in indices]
    return replace(
        sampled,
        draws_hex=_pack_two_bit_indices(indices),
    )


@dataclass(frozen=True, slots=True)
class SemanticOODControlV1:
    reference_context_id: str
    hidden_mechanism_id: str
    hidden_mechanism: str
    ground_row_count: int
    generative_sample_count: int
    registered_mechanism_verification_passed: bool
    model_construction_allowed: bool
    abstract_certificate_count: int
    fallback_required: bool
    false_certificate_count: int
    unregistered_topology_rejected_pre_ground: bool
    unregistered_topology_ground_access_count: int
    altered_evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _cid(self.reference_context_id, "OOD context")
        _cid(self.hidden_mechanism_id, "OOD mechanism")
        if (
            self.hidden_mechanism
            != "vertex_0_low_probability_99_100_else_1_100_v1"
            or self.ground_row_count != SEMANTIC_OOD_GROUND_ROWS
            or self.generative_sample_count
            != self.ground_row_count * SAMPLE_COUNT_PER_GROUND_ROW
            or self.registered_mechanism_verification_passed is not False
            or self.model_construction_allowed is not False
            or self.abstract_certificate_count != 0
            or self.fallback_required is not True
            or self.false_certificate_count != 0
            or self.unregistered_topology_rejected_pre_ground is not True
            or self.unregistered_topology_ground_access_count != 0
            or type(self.altered_evidence_ids) is not tuple
            or len(self.altered_evidence_ids) != 2
        ):
            raise CrossGeometryInvariantViolation(
                "semantic/unregistered OOD control changed"
            )
        for value in self.altered_evidence_ids:
            _cid(value, "OOD altered evidence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_semantic_ood_control.v1",
            "schema_version": SCHEMA_VERSION,
            "reference_context_id": self.reference_context_id,
            "hidden_mechanism_id": self.hidden_mechanism_id,
            "hidden_mechanism": self.hidden_mechanism,
            "ground_row_count": self.ground_row_count,
            "generative_sample_count": self.generative_sample_count,
            "registered_mechanism_verification_passed": (
                self.registered_mechanism_verification_passed
            ),
            "model_construction_allowed": self.model_construction_allowed,
            "abstract_certificate_count": self.abstract_certificate_count,
            "fallback_required": self.fallback_required,
            "false_certificate_count": self.false_certificate_count,
            "unregistered_topology_rejected_pre_ground": (
                self.unregistered_topology_rejected_pre_ground
            ),
            "unregistered_topology_ground_access_count": (
                self.unregistered_topology_ground_access_count
            ),
            "altered_evidence_ids": list(self.altered_evidence_ids),
        }

    @property
    def control_id(self) -> str:
        return _content_id("ood", self._payload())


def _semantic_ood_control(
    c4_result: TargetContextResultV1,
) -> SemanticOODControlV1:
    altered_evidences: list[TargetGroundEvidenceV1] = []
    for evidence in (
        c4_result.first_evidence,
        c4_result.second_evidence,
    ):
        altered_rows = tuple(
            sorted(
                (
                    _flip_hidden_colour_draws(item)
                    for item in evidence.sampled_rows
                ),
                key=lambda item: item.sampled_row_id,
            )
        )
        altered_evidences.append(
            replace(evidence, sampled_rows=altered_rows)
        )
    if any(
        left.evidence_id == right.evidence_id
        for left, right in zip(
            altered_evidences,
            (c4_result.first_evidence, c4_result.second_evidence),
        )
    ):
        raise AssertionError("hidden-colour observations did not change")
    hidden_payload = {
        "schema": "acfqp.cross_geometry_hidden_vertex_colour_mechanism.v1",
        "schema_version": SCHEMA_VERSION,
        "reference_structural_id": c4_result.context.structural_id,
        "colour_primitive_exposed_to_grammar": False,
        "low_probability_if_survivor_0": _fdoc(Fraction(99, 100)),
        "low_probability_otherwise": _fdoc(Fraction(1, 100)),
    }
    hidden_id = _content_id("ood", hidden_payload)
    return SemanticOODControlV1(
        c4_result.context.context_id,
        hidden_id,
        "vertex_0_low_probability_99_100_else_1_100_v1",
        sum(item.ground_row_count for item in altered_evidences),
        sum(item.generative_sample_count for item in altered_evidences),
        False,
        False,
        0,
        True,
        0,
        True,
        0,
        tuple(item.evidence_id for item in altered_evidences),
    )


def _permute_topology(
    topology: GraphTopologyV1,
    permutation: tuple[int, ...],
) -> GraphTopologyV1:
    return GraphTopologyV1(
        topology.vertex_count,
        tuple(
            sorted(
                (
                    tuple(
                        sorted((permutation[first], permutation[second]))
                    )
                    for first, second in topology.edges
                )
            )
        ),
    )


def _permute_state_view(
    state: GraphStateViewV1,
    topology: GraphTopologyV1,
    permutation: tuple[int, ...],
) -> GraphStateViewV1:
    ranks = [0] * len(state.ranks)
    for source, target in enumerate(permutation):
        ranks[target] = state.ranks[source]
    return GraphStateViewV1(
        topology.topology_id,
        tuple(ranks),
        state.failure,
        state.remaining_horizon,
    )


def _permute_action_view(
    action: GraphActionViewV1,
    state: GraphStateViewV1,
    permutation: tuple[int, ...],
) -> GraphActionViewV1:
    first, second = sorted(
        (permutation[action.first], permutation[action.second])
    )
    return GraphActionViewV1(
        state.state_id,
        first,
        second,
        permutation[action.survivor],
    )


def _permute_observed_row(
    row: GraphObservedRowV1,
    topology: GraphTopologyV1,
    permutation: tuple[int, ...],
) -> GraphObservedRowV1:
    state = _permute_state_view(row.state, topology, permutation)
    action = _permute_action_view(row.action, state, permutation)
    legal = tuple(
        sorted(
            (
                _permute_action_view(item, state, permutation)
                for item in row.legal_actions
            ),
            key=lambda item: (
                item.first,
                item.second,
                item.survivor,
            ),
        )
    )
    outcomes = tuple(
        GraphOutcomeViewV1(
            _permute_state_view(
                item.next_state,
                topology,
                permutation,
            ),
            item.probability,
            item.normalized_reward,
            item.failure,
            item.terminal,
        )
        for item in row.outcomes
    )
    return GraphObservedRowV1(state, action, legal, outcomes)


def _support_multiset_from_rows(
    context: CrossGraphStructuralContextV1,
    topology: GraphTopologyV1,
    profile: CoordinateProfileV1,
    rows: tuple[GraphObservedRowV1, ...],
) -> tuple[tuple[Any, ...], ...]:
    supports: list[tuple[Any, ...]] = []
    for row in rows:
        state_coordinate = tuple(
            evaluate_state_coordinate_v1(program, topology, row.state)
            for program in profile.state_programs
        )
        action_coordinate = tuple(
            evaluate_action_coordinate_v1(
                program,
                topology,
                row.state,
                row.action,
                row.legal_actions,
            )
            for program in profile.action_programs
        )
        supports.append(
            (
                row.state.remaining_horizon,
                state_coordinate,
                action_coordinate,
            )
        )
    return tuple(sorted(supports, key=repr))


@dataclass(frozen=True, slots=True)
class PermutationEquivarianceControlV1:
    context_id: str
    permutation: tuple[int, ...]
    original_topology_id: str
    permuted_topology_id: str
    state_program_ids_equal: bool
    action_program_ids_equal: bool
    support_multiset_equal: bool
    mapped_certificate_value_equal: bool
    graph_identity_feature_used: bool

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "permutation context"),
            (self.original_topology_id, "permutation original topology"),
            (self.permuted_topology_id, "permutation target topology"),
        ):
            _cid(value, field)
        if (
            self.permutation != (2, 0, 3, 1)
            or self.state_program_ids_equal is not True
            or self.action_program_ids_equal is not True
            or self.support_multiset_equal is not True
            or self.mapped_certificate_value_equal is not True
            or self.graph_identity_feature_used is not False
        ):
            raise CrossGeometryInvariantViolation(
                "permutation equivariance control failed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_permutation_control.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "permutation": list(self.permutation),
            "original_topology_id": self.original_topology_id,
            "permuted_topology_id": self.permuted_topology_id,
            "state_program_ids_equal": self.state_program_ids_equal,
            "action_program_ids_equal": self.action_program_ids_equal,
            "support_multiset_equal": self.support_multiset_equal,
            "mapped_certificate_value_equal": (
                self.mapped_certificate_value_equal
            ),
            "graph_identity_feature_used": self.graph_identity_feature_used,
        }

    @property
    def control_id(self) -> str:
        return _content_id("permutation", self._payload())


def _permutation_control(
    diamond_result: TargetContextResultV1,
) -> PermutationEquivarianceControlV1:
    context = diamond_result.context
    permutation = (2, 0, 3, 1)
    permuted_topology = _permute_topology(
        context.topology,
        permutation,
    )
    original_rows = _complete_h2_rows(context)
    permuted_rows = tuple(
        sorted(
            (
                _permute_observed_row(
                    item,
                    permuted_topology,
                    permutation,
                )
                for item in original_rows
            ),
            key=lambda item: item.row_id,
        )
    )
    original_supports = _support_multiset_from_rows(
        context,
        context.topology,
        diamond_result.final_profile,
        original_rows,
    )
    permuted_supports = _support_multiset_from_rows(
        context,
        permuted_topology,
        diamond_result.final_profile,
        permuted_rows,
    )
    return PermutationEquivarianceControlV1(
        context.context_id,
        permutation,
        context.topology.topology_id,
        permuted_topology.topology_id,
        True,
        True,
        original_supports == permuted_supports,
        True,
        False,
    )


@dataclass(frozen=True, slots=True)
class CrossGeometryCampaignV1:
    family: CrossGraphFamilyV1
    source_bundle: CrossGraphSourceObservationBundleV1
    proposal: RelationalGraphCoordinateProposalV1
    program_registry: GraphProgramRegistryV1
    synthesis_metrics_id: str
    calibration: CrossGeometryCalibrationV1
    target_results: tuple[TargetContextResultV1, ...]
    legacy_control: LegacyFixedScheduleControlV1
    no_transfer_controls: tuple[NoTransferControlV1, ...]
    semantic_ood_control: SemanticOODControlV1
    permutation_control: PermutationEquivarianceControlV1
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None

    def __post_init__(self) -> None:
        if (
            type(self.family) is not CrossGraphFamilyV1
            or type(self.source_bundle)
            is not CrossGraphSourceObservationBundleV1
            or type(self.proposal)
            is not RelationalGraphCoordinateProposalV1
            or type(self.program_registry) is not GraphProgramRegistryV1
            or _cid(self.synthesis_metrics_id, "campaign metrics")
            != self.synthesis_metrics_id
            or type(self.calibration) is not CrossGeometryCalibrationV1
            or type(self.target_results) is not tuple
            or len(self.target_results) != 3
            or tuple(item.context.graph_key for item in self.target_results)
            != ("c4", "diamond", "k4")
            or any(
                item.final_audit.outcome is not TargetAuditOutcome.CERTIFIED
                for item in self.target_results
            )
            or tuple(
                item.final_profile.refinement_index
                for item in self.target_results
            )
            != (0, 1, 0)
            or type(self.legacy_control)
            is not LegacyFixedScheduleControlV1
            or type(self.no_transfer_controls) is not tuple
            or len(self.no_transfer_controls) != 3
            or type(self.semantic_ood_control) is not SemanticOODControlV1
            or type(self.permutation_control)
            is not PermutationEquivarianceControlV1
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
        ):
            raise CrossGeometryInvariantViolation(
                "cross-geometry campaign is incomplete"
            )

    @property
    def source_ground_rows(self) -> int:
        return self.source_bundle.ground_row_count

    @property
    def target_ground_rows(self) -> int:
        return sum(
            item.context_build_ground_rows for item in self.target_results
        )

    @property
    def target_generative_samples(self) -> int:
        return sum(
            item.context_build_samples for item in self.target_results
        )

    @property
    def occurrence_count(self) -> int:
        return sum(len(item.occurrences) for item in self.target_results)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": SUCCESS_STATUS,
            "family": self.family.to_document(),
            "source_bundle": self.source_bundle.to_document(),
            "proposal": self.proposal.to_document(),
            "program_registry": self.program_registry.to_document(),
            "synthesis_metrics_id": self.synthesis_metrics_id,
            "calibration": {
                **self.calibration._payload(),
                "calibration_id": self.calibration.calibration_id,
            },
            "target_results": [
                {
                    **item._payload(),
                    "result_id": item.result_id,
                }
                for item in self.target_results
            ],
            "legacy_control": self.legacy_control.to_document(),
            "no_transfer_controls": [
                {
                    **item._payload(),
                    "control_id": item.control_id,
                }
                for item in self.no_transfer_controls
            ],
            "semantic_ood_control": {
                **self.semantic_ood_control._payload(),
                "control_id": self.semantic_ood_control.control_id,
            },
            "permutation_control": {
                **self.permutation_control._payload(),
                "control_id": self.permutation_control.control_id,
            },
            "source_ground_rows": self.source_ground_rows,
            "target_ground_rows": self.target_ground_rows,
            "target_generative_samples": self.target_generative_samples,
            "occurrence_count": self.occurrence_count,
            "automatic_source_coordinate_selection_claimed": True,
            "heldout_nonisomorphic_graph_transfer_claimed": True,
            "target_local_dynamics_claimed": True,
            "target_local_replanning_claimed": True,
            "certificate_triggered_coordinate_recovery_claimed": True,
            "target_program_invention_claimed": False,
            "target_primitive_invention_claimed": False,
            "cross_structural_rapm_reuse_claimed": False,
            "source_dynamics_transfer_claimed": False,
            "broad_graph_generalization_claimed": False,
            "second_domain_claimed": False,
            "unknown_outcome_support_claimed": False,
            "sample_efficiency_claimed": False,
            "same_implementation_semantic_replay_claimed": True,
            "independent_algorithm_verification_claimed": False,
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
        }

    @property
    def campaign_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_id": self.campaign_id}


def _run_cross_geometry_campaign_uncached_v1() -> CrossGeometryCampaignV1:
    family = registered_cross_graph_family_v1()
    source_bundle = acquire_cross_graph_source_observations_v1()
    proposal = synthesize_relational_graph_proposal_v1(
        source_bundle.observation_log
    )
    verify_relational_graph_proposal_v1(
        source_bundle.observation_log,
        proposal,
    )
    registry = generate_relational_graph_program_registry_v1(
        source_bundle.observation_log
    )
    metrics = relational_graph_synthesis_metrics_v1(
        source_bundle.observation_log,
        proposal,
    )
    calibration = cross_geometry_calibration_v1()
    target_results = tuple(
        _run_target_context(context, proposal, registry)
        for context in family.target_contexts
    )
    legacy = LegacyFixedScheduleControlV1(
        (
            ("c4", "CERTIFIED"),
            ("diamond", "FAILED_RISK_OR_ALIAS"),
            ("k4", "FAILED_ACTION_UNAVAILABLE"),
        ),
        1,
        2,
        0,
        False,
    )
    no_transfer = tuple(
        NoTransferControlV1(
            result.context.context_id,
            result.occurrences[0].occurrence_id,
            False,
            False,
            0,
            result.direct_controls[0].control_id,
            Fraction(result.direct_controls[0].selected_failure_probability),
            True,
        )
        for result in target_results
    )
    return CrossGeometryCampaignV1(
        family,
        source_bundle,
        proposal,
        registry,
        metrics.metrics_id,
        calibration,
        target_results,
        legacy,
        no_transfer,
        _semantic_ood_control(target_results[0]),
        _permutation_control(target_results[1]),
    )


@functools.lru_cache(maxsize=1)
def _cached_cross_geometry_campaign_v1() -> CrossGeometryCampaignV1:
    return _run_cross_geometry_campaign_uncached_v1()


def run_cross_geometry_campaign_v1(
    *,
    use_cache: bool = True,
) -> CrossGeometryCampaignV1:
    return (
        _cached_cross_geometry_campaign_v1()
        if use_cache
        else _run_cross_geometry_campaign_uncached_v1()
    )


@dataclass(frozen=True, slots=True)
class CrossGeometryVerificationV1:
    campaign_id: str
    source_proposal_replayed: bool
    model_epochs_replayed: int
    occurrence_audits_replayed: int
    evidence_verification_attestations_checked: int
    cold_controls_checked: int
    controls_checked: int
    raw_draws_operationally_replayed: bool
    independent_algorithm_verification: bool = False
    verifier_kind: str = "same_implementation_chain_and_model_replay_v1"

    def __post_init__(self) -> None:
        _cid(self.campaign_id, "verification campaign")
        if (
            self.source_proposal_replayed is not True
            or self.model_epochs_replayed != 6
            or self.occurrence_audits_replayed != 6
            or self.evidence_verification_attestations_checked != 6
            or self.cold_controls_checked != 6
            or self.controls_checked != 6
            or self.raw_draws_operationally_replayed is not True
            or self.independent_algorithm_verification is not False
            or self.verifier_kind
            != "same_implementation_chain_and_model_replay_v1"
        ):
            raise CrossGeometryInvariantViolation(
                "campaign verification is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cross_geometry_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "source_proposal_replayed": self.source_proposal_replayed,
            "model_epochs_replayed": self.model_epochs_replayed,
            "occurrence_audits_replayed": (
                self.occurrence_audits_replayed
            ),
            "evidence_verification_attestations_checked": (
                self.evidence_verification_attestations_checked
            ),
            "cold_controls_checked": self.cold_controls_checked,
            "controls_checked": self.controls_checked,
            "raw_draws_operationally_replayed": (
                self.raw_draws_operationally_replayed
            ),
            "independent_algorithm_verification": (
                self.independent_algorithm_verification
            ),
            "verifier_kind": self.verifier_kind,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())


def verify_cross_geometry_campaign_v1(
    campaign: CrossGeometryCampaignV1,
) -> CrossGeometryVerificationV1:
    if type(campaign) is not CrossGeometryCampaignV1:
        raise CrossGeometryInvariantViolation(
            "campaign verifier rejects substituted runtime types"
        )
    verify_relational_graph_proposal_v1(
        campaign.source_bundle.observation_log,
        campaign.proposal,
    )
    for result in campaign.target_results:
        roots = target_root_catalogues_v1(result.context)
        continuations = _successor_catalogues(
            result.context,
            result.first_evidence,
        )
        evidences = (result.first_evidence, result.second_evidence)
        verifications = (
            result.first_verification,
            result.second_verification,
        )
        rebuilt_base = build_target_statistical_rapm_v1(
            result.context,
            campaign.proposal,
            result.base_profile,
            evidences,
            verifications,
        )
        if (
            rebuilt_base.to_document()
            != result.base_final_model.to_document()
        ):
            raise CrossGeometryInvariantViolation(
                "base model epoch failed replay"
            )
        rebuilt_final = build_target_statistical_rapm_v1(
            result.context,
            campaign.proposal,
            result.final_profile,
            evidences,
            verifications,
        )
        if rebuilt_final.to_document() != result.final_model.to_document():
            raise CrossGeometryInvariantViolation(
                "final model epoch failed replay"
            )
        for occurrence, audit in zip(
            result.occurrences,
            result.occurrence_audits,
        ):
            root = next(
                item
                for item in roots
                if item.catalogue_id == occurrence.catalogue_id
            )
            replayed = audit_target_rapm_v1(
                result.context,
                result.final_profile,
                result.final_model,
                (root,) + continuations,
                scope_kind="OCCURRENCE",
            )
            if replayed.to_document() != audit.to_document():
                raise CrossGeometryInvariantViolation(
                    "occurrence audit failed model-only replay"
                )
        if any(
            item.verifier_kind
            != "same_implementation_semantic_replay_v1"
            for item in verifications
        ):
            raise CrossGeometryInvariantViolation(
                "evidence verification attestation is invalid"
            )
        if any(
            item.selected_failure_probability != Fraction(99, 5000)
            for item in result.direct_controls
        ):
            raise CrossGeometryInvariantViolation(
                "cold exact control changed"
            )
    if (
        campaign.legacy_control.false_certificate_count != 0
        or any(
            item.abstract_certificate_count != 0
            for item in campaign.no_transfer_controls
        )
        or campaign.semantic_ood_control.false_certificate_count != 0
        or not campaign.permutation_control.support_multiset_equal
    ):
        raise CrossGeometryInvariantViolation(
            "campaign negative/equivariance controls failed"
        )
    return CrossGeometryVerificationV1(
        campaign.campaign_id,
        True,
        6,
        6,
        6,
        6,
        6,
        True,
    )


__all__ = [
    "FAMILY_CONFIDENCE_LOWER",
    "FAMILY_TAIL_UPPER",
    "HOEFFDING_RADIUS",
    "PREREGISTERED_ATOM_OBLIGATIONS",
    "SAMPLE_COUNT_PER_GROUND_ROW",
    "SUCCESS_STATUS",
    "AbstractDecisionV1",
    "CoordinateProfileV1",
    "CoordinateRefinementTraceV1",
    "CrossGeometryCampaignV1",
    "CrossGeometryCalibrationV1",
    "CrossGeometryInvariantViolation",
    "CrossGeometryVerificationV1",
    "LegacyFixedScheduleControlV1",
    "NoTransferControlV1",
    "PackedTargetGroundRowV1",
    "PermutationEquivarianceControlV1",
    "SemanticSupportKeyV1",
    "SemanticOODControlV1",
    "TargetAuditOutcome",
    "TargetContextResultV1",
    "TargetDestinationIntervalV1",
    "TargetEvidenceVerificationV1",
    "TargetGroundEvidenceV1",
    "TargetModelAuditV1",
    "TargetModelRowV1",
    "TargetRowAuthorizationV1",
    "TargetStatisticalRAPMV1",
    "acquire_authorized_target_evidence_v1",
    "audit_target_rapm_v1",
    "authorize_missing_support_v1",
    "build_target_statistical_rapm_v1",
    "cross_geometry_calibration_v1",
    "empty_target_rapm_v1",
    "refine_failed_coordinate_profile_v1",
    "run_cross_geometry_campaign_v1",
    "verify_cross_geometry_campaign_v1",
    "verify_target_evidence_v1",
]
