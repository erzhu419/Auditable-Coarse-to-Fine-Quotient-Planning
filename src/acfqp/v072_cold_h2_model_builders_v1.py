"""Kernel-free V0-072 cold-H2 direct and relational model construction.

The builder consumes an already-frozen :class:`V072ColdH2ClosureBundleV1`
and one independently verified confidence-row projection for every closure
row.  It never opens an observer, transition kernel, hidden law, or source
archive.

Two models are emitted over the exact same physical interval-simplex rows:

* ground-direct catalogues preserve ground state/action identities;
* quotient catalogues preserve those identities but replace coordinate keys
  with label-free, observation-driven behavioral coordinates and attach a
  fixed distinct-action concretizer.

The robust planner's legacy model schema permits only one global ``OTHER``.
V0-072 instead requires a row-bound adversarial escape, so this module defines
the strict multi-OTHER model container while continuing to use the exact
``IntervalSimplexRowV1`` and related planner value objects.

The original rank-cap-4 development profile remains unchanged.  A separate
rank-cap-6 registered builder accepts only exact remote-anchor-bound
confidence projections and confirmatory closure evidence; it never converts
or relabels a development artifact into target evidence.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping, Protocol, runtime_checkable

from acfqp.phase3e_ids import (
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import v072_cold_h2_closure_v1 as closure
from acfqp import v072_confidence_row_projection_v1 as row_projection
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_cold_h2_direct_relational_model_builder_v0"

DEVELOPMENT_RANK_PROFILE = (
    "DEVELOPMENT_SYNTHETIC_K4_RANK_CAP_4_NONCONFIRMATORY_NONMIGRATABLE"
)
PRODUCTION_RANK_PROFILE = "PRODUCTION_G2048_RANK_CAP_6_REGISTERED"
REGISTERED_TARGET_MODEL_BUILD_STATUS = (
    "ENABLED_FOR_EXACT_REGISTERED_CONFIDENCE_PROJECTIONS"
)
REGISTERED_TARGET_MODEL_INDEPENDENT_REPLAY_STATUS = (
    "SEPARATE_IDENTITY_BOUND_ATTESTATION_REQUIRED"
)
V0066_SOURCE_SKELETON_ID = (
    "77a9666172fb5cebf30820b12075fef92e190f3ccda6cdf44e4c902c7dc73322"
)
V0066_STATE_PROGRAM_ID = (
    "051e6331bd01c4df41a889d0cc248d7ad48c3cc0815a4b91d2597f36ceae2fa1"
)
V0066_ACTION_PROGRAM_ID = (
    "59ae6240e21b48097e94f3259e024aeb0341d21128bff5604c1c2ea3cf7e80e7"
)
V0068_BASE_COORDINATE_PROFILE_ID = (
    "9b551f31e5ec0fa28135c2d3ea5f4e5b27b1ce1aa404f7211c702657af7fdfb7"
)
BOUNDED_REFINEMENT_STATUS = (
    "TYPED_ABSENT_UNTIL_FAILED_PROOF_GENERATION"
)
COORDINATE_DERIVATION = (
    "V0066_BASE_PROGRAM_PUBLIC_REPLAY_WITH_TYPED_ABSENT_REFINEMENT"
)
DEVELOPMENT_RISK_TOLERANCE = Fraction(1, 20)
DEVELOPMENT_REWARD_CEILING = Fraction(1, 8)
PRODUCTION_RISK_TOLERANCE = Fraction(1, 20)
PRODUCTION_REWARD_CEILING = Fraction(3, 64)
FORBIDDEN_COORDINATE_KEYS = frozenset(
    {
        "arm",
        "source",
        "source_rank",
        "vertex",
        "vertex_id",
        "label",
        "state_label",
        "action_index",
        "index",
        "d4",
        "orbit",
        "lower",
        "upper",
        "reward",
        "probability",
        "count",
        "checkpoint",
        "confidence",
        "physical",
        "row_id",
        "state_id",
        "action_id",
        "vertex_label",
    }
)


class V072ColdH2ModelBuilderInvariantViolation(ValueError):
    """A projection inventory, coordinate, catalogue, or model is invalid."""


class RegisteredTargetColdH2ModelBuildLockedV1(RuntimeError):
    """No final target authority exists for the production cap-6 profile."""


class ColdH2ModelKindV1(str, Enum):
    GROUND_DIRECT = "GROUND_DIRECT"
    OBSERVATION_RELATIONAL_QUOTIENT = "OBSERVATION_RELATIONAL_QUOTIENT"


class RelationalCoordinateRoleV1(str, Enum):
    STATE = "STATE"
    ACTION = "ACTION"
    SUPPORT = "SUPPORT"


class RowProjectionEvidenceClassV1(str, Enum):
    DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY = (
        "DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY"
    )
    REGISTERED_TARGET_VERIFIED = "REGISTERED_TARGET_VERIFIED"


DOMAIN_TAGS = {
    "ground_state": "acfqp:v072-cold-model-ground-state:v1",
    "ground_action": "acfqp:v072-cold-model-ground-action:v1",
    "observed_destination": (
        "acfqp:v072-cold-model-observed-destination:v1"
    ),
    "other_destination": (
        "acfqp:v072-cold-model-row-bound-other-destination:v1"
    ),
    "projection_binding": (
        "acfqp:v072-cold-model-confidence-row-projection-binding:v1"
    ),
    "relational_context": (
        "acfqp:v072-cold-model-public-relational-context:v1"
    ),
    "coordinate": "acfqp:v072-cold-model-relational-coordinate:v1",
    "global_other": (
        "acfqp:v072-cold-model-absorbing-policy-abort-failure:v1"
    ),
    "collapse_entry": (
        "acfqp:v072-cold-model-row-bound-other-collapse-entry:v1"
    ),
    "collapse_proof": (
        "acfqp:v072-cold-model-row-bound-other-collapse-proof:v1"
    ),
    "planner_projection": (
        "acfqp:v072-cold-model-planner-projection:v1"
    ),
    "direct_snapshot": (
        "acfqp:v072-cold-model-ground-direct-checkpoint-snapshot:v1"
    ),
    "model": "acfqp:v072-cold-model-interval-simplex-model:v1",
    "pair": "acfqp:v072-cold-model-direct-quotient-pair:v1",
    "registered_relational_context": (
        "acfqp:v072-registered-cold-h2-relational-context:v1"
    ),
    "registered_model": "acfqp:v072-registered-cold-h2-model:v1",
    "registered_global_other": (
        "acfqp:v072-registered-cold-h2-global-other:v1"
    ),
    "registered_collapse": (
        "acfqp:v072-registered-cold-h2-other-collapse-proof:v1"
    ),
    "registered_pair": (
        "acfqp:v072-registered-cold-h2-direct-quotient-pair:v1"
    ),
}


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072ColdH2ModelBuilderInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072ColdH2ModelBuilderInvariantViolation(
            f"{field_name} must be one full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072ColdH2ModelBuilderInvariantViolation(
            "model arithmetic must remain exact Fraction"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


@dataclass(frozen=True, slots=True)
class ColdH2PublicRelationalContextV1:
    """Public topology used to replay the frozen V0-066 base programs."""

    context_id: str
    topology_id: str
    vertex_count: int
    edges: tuple[tuple[int, int], ...]
    rank_cap: int = 4
    source_skeleton_id: str = V0066_SOURCE_SKELETON_ID
    state_program_id: str = V0066_STATE_PROGRAM_ID
    action_program_id: str = V0066_ACTION_PROGRAM_ID
    coordinate_profile_id: str = V0068_BASE_COORDINATE_PROFILE_ID
    bounded_refinement_status: str = BOUNDED_REFINEMENT_STATUS
    _relational_context_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.context_id, "relational context"),
            (self.topology_id, "public topology"),
            (self.source_skeleton_id, "portable source skeleton"),
            (self.state_program_id, "portable state program"),
            (self.action_program_id, "portable action program"),
            (
                self.coordinate_profile_id,
                "observation-support coordinate profile",
            ),
        ):
            _cid(value, label)
        if (
            type(self.vertex_count) is not int
            or self.vertex_count <= 1
            or type(self.edges) is not tuple
            or not self.edges
            or any(
                type(edge) is not tuple
                or len(edge) != 2
                or any(type(vertex) is not int for vertex in edge)
                or not 0 <= edge[0] < edge[1] < self.vertex_count
                for edge in self.edges
            )
            or self.edges != tuple(sorted(set(self.edges)))
            or self.rank_cap != 4
            or self.source_skeleton_id != V0066_SOURCE_SKELETON_ID
            or self.state_program_id != V0066_STATE_PROGRAM_ID
            or self.action_program_id != V0066_ACTION_PROGRAM_ID
            or self.coordinate_profile_id
            != V0068_BASE_COORDINATE_PROFILE_ID
            or self.bounded_refinement_status
            != BOUNDED_REFINEMENT_STATUS
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "public relational context is noncanonical or target-like"
            )
        object.__setattr__(
            self,
            "_relational_context_id",
            _content_id("relational_context", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_model_public_relational_context.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "topology_id": self.topology_id,
            "vertex_count": self.vertex_count,
            "edges": [list(edge) for edge in self.edges],
            "rank_cap": 4,
            "source_skeleton_id": self.source_skeleton_id,
            "state_program_id": self.state_program_id,
            "action_program_id": self.action_program_id,
            "coordinate_profile_id": self.coordinate_profile_id,
            "bounded_refinement": {
                "kind": "NOT_APPLICABLE",
                "status": self.bounded_refinement_status,
                "refinement_generation_id": None,
            },
            "public_semantics_only": True,
            "source_observation_rows_imported": False,
            "source_feature_ranks_imported": False,
        }

    @property
    def relational_context_id(self) -> str:
        return self._relational_context_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "relational_context_id": self.relational_context_id,
        }


def _public_ranks(
    relational_context: ColdH2PublicRelationalContextV1,
    state: closure.ColdPublicStateV1,
) -> tuple[int, ...]:
    if (
        type(relational_context) is not ColdH2PublicRelationalContextV1
        or type(state) is not closure.ColdPublicStateV1
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "relational state replay requires exact public inputs"
        )
    document = dict(state.document)
    ranks = document.get("ranks")
    if (
        document.get("context_id") != relational_context.context_id
        or document.get("topology_id") != relational_context.topology_id
        or type(ranks) is not list
        or len(ranks) != relational_context.vertex_count
        or any(
            type(rank) is not int
            or not 0 <= rank <= relational_context.rank_cap
            for rank in ranks
        )
        or type(document.get("failure")) is not bool
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "public state lacks canonical topology/rank semantics"
        )
    return tuple(ranks)


def _public_action(
    relational_context: ColdH2PublicRelationalContextV1,
    action: closure.ColdPublicActionV1,
) -> tuple[int, int, int]:
    if type(action) is not closure.ColdPublicActionV1:
        raise V072ColdH2ModelBuilderInvariantViolation(
            "relational action replay requires one public action"
        )
    document = dict(action.document)
    raw = document.get("action")
    if (
        document.get("context_id") != relational_context.context_id
        or document.get("topology_id") != relational_context.topology_id
        or type(raw) is not list
        or len(raw) != 3
        or any(type(vertex) is not int for vertex in raw)
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "public action lacks canonical merge/survivor semantics"
        )
    first, second, survivor = raw
    edge = tuple(sorted((first, second)))
    if (
        edge not in relational_context.edges
        or survivor not in edge
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "public action is outside the public topology"
        )
    return first, second, survivor


def _replay_catalogue_relational_values(
    relational_context: ColdH2PublicRelationalContextV1,
    catalogue: closure.ColdPublicCatalogueV1,
) -> tuple[int, dict[str, int]]:
    ranks = _public_ranks(relational_context, catalogue.state)
    expected_actions = tuple(
        sorted(
            (first, second, survivor)
            for first, second in relational_context.edges
            if ranks[first] > 0 and ranks[first] == ranks[second]
            for survivor in (first, second)
        )
    )
    actual_by_record = {
        action.action_record_id: _public_action(
            relational_context, action
        )
        for action in catalogue.actions
    }
    if (
        tuple(sorted(actual_by_record.values())) != expected_actions
        or len(actual_by_record) != len(expected_actions)
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "cold catalogue is not complete under public graph semantics"
        )
    active = {vertex for vertex, rank in enumerate(ranks) if rank > 0}
    neighbours: dict[int, set[int]] = {
        vertex: set() for vertex in range(relational_context.vertex_count)
    }
    for first, second in relational_context.edges:
        neighbours[first].add(second)
        neighbours[second].add(first)
    action_values = {
        record_id: len(neighbours[action[2]] & active)
        for record_id, action in actual_by_record.items()
    }
    return len(expected_actions), action_values


def replay_v0066_base_coordinate_values_v1(
    relational_context: ColdH2PublicRelationalContextV1,
    catalogue: closure.ColdPublicCatalogueV1,
) -> tuple[int, tuple[tuple[str, int], ...]]:
    """Public deterministic replay of the two frozen V0-066 base programs."""

    state_value, action_values = _replay_catalogue_relational_values(
        relational_context, catalogue
    )
    return state_value, tuple(sorted(action_values.items()))


def ground_state_id_v1(
    context_id: str,
    state: closure.ColdPublicStateV1,
    remaining_horizon: int,
) -> str:
    _cid(context_id, "ground-state context")
    if (
        type(state) is not closure.ColdPublicStateV1
        or remaining_horizon not in (1, 2)
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "ground state requires exact cold public semantics"
        )
    return _content_id(
        "ground_state",
        {
            "schema": "acfqp.v072_cold_model_ground_state.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "state_record_id": state.state_record_id,
            "semantic_state_id": state.semantic_state_id,
            "remaining_horizon": remaining_horizon,
            "ground_identity_preserved": True,
        },
    )


def ground_action_id_v1(
    context_id: str,
    state: closure.ColdPublicStateV1,
    remaining_horizon: int,
    action: closure.ColdPublicActionV1,
) -> str:
    state_id = ground_state_id_v1(context_id, state, remaining_horizon)
    if type(action) is not closure.ColdPublicActionV1:
        raise V072ColdH2ModelBuilderInvariantViolation(
            "ground action requires exact cold public semantics"
        )
    return _content_id(
        "ground_action",
        {
            "schema": "acfqp.v072_cold_model_ground_action.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "state_id": state_id,
            "state_record_id": state.state_record_id,
            "remaining_horizon": remaining_horizon,
            "action_record_id": action.action_record_id,
            "semantic_action_id": action.semantic_action_id,
            "ground_identity_preserved": True,
        },
    )


def observed_destination_id_v1(
    row: closure.ColdRowEvidenceV1,
    descriptor: closure.ColdOutcomeDescriptorV1,
) -> str:
    if (
        type(row) is not closure.ColdRowEvidenceV1
        or type(descriptor) is not closure.ColdOutcomeDescriptorV1
        or descriptor not in row.discovery_support
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "observed destination must come from discovery-frozen support"
        )
    return _content_id(
        "observed_destination",
        {
            "schema": "acfqp.v072_cold_model_observed_destination.v1",
            "schema_version": SCHEMA_VERSION,
            "row_evidence_id": row.row_evidence_id,
            "descriptor_record_id": descriptor.descriptor_record_id,
            "semantic_descriptor_id": descriptor.semantic_descriptor_id,
            "row_bound": True,
        },
    )


def row_bound_other_destination_id_v1(
    row: closure.ColdRowEvidenceV1,
) -> str:
    if type(row) is not closure.ColdRowEvidenceV1:
        raise V072ColdH2ModelBuilderInvariantViolation(
            "row-bound OTHER requires exact cold row evidence"
        )
    return _content_id(
        "other_destination",
        {
            "schema": (
                "acfqp.v072_cold_model_row_bound_other_destination.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": row.context_id,
            "row_evidence_id": row.row_evidence_id,
            "physical_evidence_id": row.physical_evidence_id,
            "state_semantic_id": row.state.semantic_state_id,
            "remaining_horizon": row.remaining_horizon,
            "action_semantic_id": row.action.semantic_action_id,
            "adversarial_failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
        },
    )


def destination_for_descriptor_v1(
    row: closure.ColdRowEvidenceV1,
    descriptor: closure.ColdOutcomeDescriptorV1,
) -> robust.RegisteredDestinationV1:
    destination_id = observed_destination_id_v1(row, descriptor)
    if descriptor.failure:
        category = robust.DestinationCategory.FAILURE
        state_id = None
    elif descriptor.terminal:
        category = robust.DestinationCategory.SUCCESS_TERMINAL
        state_id = None
    else:
        assert descriptor.successor_state is not None
        category = robust.DestinationCategory.ACTIVE_STATE
        state_id = ground_state_id_v1(
            row.context_id,
            descriptor.successor_state,
            row.remaining_horizon - 1,
        )
    return robust.RegisteredDestinationV1(
        destination_id,
        category,
        state_id,
    )


def other_destination_for_row_v1(
    row: closure.ColdRowEvidenceV1,
) -> robust.RegisteredDestinationV1:
    return robust.RegisteredDestinationV1(
        row_bound_other_destination_id_v1(row),
        robust.DestinationCategory.OTHER,
    )


@runtime_checkable
class VerifiedConfidenceRowProjectionProtocolV1(Protocol):
    @property
    def context_id(self) -> str: ...

    @property
    def row_evidence_id(self) -> str: ...

    @property
    def physical_evidence_id(self) -> str: ...

    @property
    def support_epoch_id(self) -> str: ...

    @property
    def confidence_snapshot_id(self) -> str: ...

    @property
    def row_replay_verification_id(self) -> str: ...

    @property
    def discovery_transcript_id(self) -> str: ...

    @property
    def validation_transcript_id(self) -> str: ...

    @property
    def validation_prefix_id(self) -> str: ...

    @property
    def selected_checkpoint_draw_count(self) -> int: ...

    @property
    def projection_id(self) -> str: ...

    @property
    def projection_verification_id(self) -> str: ...

    @property
    def state_semantic_id(self) -> str: ...

    @property
    def remaining_horizon(self) -> int: ...

    @property
    def action_semantic_id(self) -> str: ...

    @property
    def discovery_support_descriptor_ids(self) -> tuple[str, ...]: ...

    @property
    def validation_novel_descriptor_ids(self) -> tuple[str, ...]: ...

    @property
    def interval_row(self) -> robust.IntervalSimplexRowV1: ...

    @property
    def destinations(self) -> tuple[robust.RegisteredDestinationV1, ...]: ...

    @property
    def rank_cap(self) -> int: ...

    @property
    def rank_profile(self) -> str: ...

    @property
    def evidence_class(self) -> RowProjectionEvidenceClassV1: ...

    @property
    def registered_target_evidence(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class VerifiedColdH2ConfidenceRowProjectionV1:
    context_id: str
    row_evidence_id: str
    physical_evidence_id: str
    support_epoch_id: str
    confidence_snapshot_id: str
    row_replay_verification_id: str
    discovery_transcript_id: str
    validation_transcript_id: str
    validation_prefix_id: str
    selected_checkpoint_draw_count: int
    source_projection_id: str
    projection_verification_id: str
    state_semantic_id: str
    remaining_horizon: int
    action_semantic_id: str
    discovery_support_descriptor_ids: tuple[str, ...]
    validation_novel_descriptor_ids: tuple[str, ...]
    interval_row: robust.IntervalSimplexRowV1
    destinations: tuple[robust.RegisteredDestinationV1, ...]
    rank_cap: int
    rank_profile: str
    evidence_class: RowProjectionEvidenceClassV1
    registered_target_evidence: bool
    _projection_binding_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.context_id, "projection context"),
            (self.row_evidence_id, "projection closure row"),
            (self.physical_evidence_id, "projection physical evidence"),
            (self.support_epoch_id, "projection support epoch"),
            (self.confidence_snapshot_id, "projection confidence snapshot"),
            (
                self.row_replay_verification_id,
                "projection row replay verification",
            ),
            (
                self.discovery_transcript_id,
                "projection discovery transcript",
            ),
            (
                self.validation_transcript_id,
                "projection validation transcript",
            ),
            (
                self.validation_prefix_id,
                "projection validation prefix",
            ),
            (self.source_projection_id, "source confidence projection"),
            (
                self.projection_verification_id,
                "confidence projection verification",
            ),
            (self.state_semantic_id, "projection state semantic"),
            (self.action_semantic_id, "projection action semantic"),
        ):
            _cid(value, label)
        for sequence, label in (
            (
                self.discovery_support_descriptor_ids,
                "discovery support descriptors",
            ),
            (
                self.validation_novel_descriptor_ids,
                "validation novel descriptors",
            ),
        ):
            if sequence != tuple(sorted(set(sequence))):
                raise V072ColdH2ModelBuilderInvariantViolation(
                    f"{label} must be sorted and distinct"
                )
            for item in sequence:
                _cid(item, label)
        if (
            self.remaining_horizon not in (1, 2)
            or type(self.selected_checkpoint_draw_count) is not int
            or self.selected_checkpoint_draw_count
            not in (2_048, 4_096, 8_192, 16_384)
            or type(self.interval_row) is not robust.IntervalSimplexRowV1
            or type(self.destinations) is not tuple
            or not self.destinations
            or any(
                type(item) is not robust.RegisteredDestinationV1
                for item in self.destinations
            )
            or tuple(item.destination_id for item in self.destinations)
            != tuple(
                sorted({item.destination_id for item in self.destinations})
            )
            or {
                item.destination_id for item in self.destinations
            }
            != {
                item.destination_id for item in self.interval_row.masses
            }
            or sum(
                item.category is robust.DestinationCategory.OTHER
                for item in self.destinations
            )
            != 1
            or self.interval_row.other_destination_id
            not in {
                item.destination_id
                for item in self.destinations
                if item.category is robust.DestinationCategory.OTHER
            }
            or self.interval_row.remaining_horizon
            != self.remaining_horizon
            or self.interval_row.reward_lower
            != self.interval_row.reward_upper
            or self.rank_cap != 4
            or self.rank_profile != DEVELOPMENT_RANK_PROFILE
            or self.evidence_class
            is not (
                RowProjectionEvidenceClassV1
                .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
            )
            or self.registered_target_evidence is not False
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "verified confidence-row projection is malformed or target-like"
            )
        object.__setattr__(
            self,
            "_projection_binding_id",
            _content_id("projection_binding", self._payload()),
        )

    @property
    def projection_id(self) -> str:
        return self.source_projection_id

    @property
    def projection_binding_id(self) -> str:
        return self._projection_binding_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_cold_model_confidence_row_projection_binding.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "row_evidence_id": self.row_evidence_id,
            "physical_evidence_id": self.physical_evidence_id,
            "support_epoch_id": self.support_epoch_id,
            "confidence_snapshot_id": self.confidence_snapshot_id,
            "row_replay_verification_id": (
                self.row_replay_verification_id
            ),
            "discovery_transcript_id": self.discovery_transcript_id,
            "validation_transcript_id": self.validation_transcript_id,
            "validation_prefix_id": self.validation_prefix_id,
            "selected_checkpoint_draw_count": (
                self.selected_checkpoint_draw_count
            ),
            "source_projection_id": self.source_projection_id,
            "projection_verification_id": (
                self.projection_verification_id
            ),
            "state_semantic_id": self.state_semantic_id,
            "remaining_horizon": self.remaining_horizon,
            "action_semantic_id": self.action_semantic_id,
            "discovery_support_descriptor_ids": list(
                self.discovery_support_descriptor_ids
            ),
            "validation_novel_descriptor_ids": list(
                self.validation_novel_descriptor_ids
            ),
            "interval_row_id": self.interval_row.row_id,
            "destination_entry_ids": [
                item.registry_entry_id for item in self.destinations
            ],
            "rank_cap": self.rank_cap,
            "rank_profile": self.rank_profile,
            "evidence_class": self.evidence_class.value,
            "registered_target_evidence": False,
        }

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "interval_row": self.interval_row.to_document(),
            "destinations": [
                item.to_document() for item in self.destinations
            ],
            "projection_binding_id": self.projection_binding_id,
        }


def bind_verified_confidence_row_projection_v1(
    value: VerifiedConfidenceRowProjectionProtocolV1,
) -> VerifiedColdH2ConfidenceRowProjectionV1:
    if not isinstance(value, VerifiedConfidenceRowProjectionProtocolV1):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "confidence-row adapter does not implement the narrow protocol"
        )
    if type(value) is VerifiedColdH2ConfidenceRowProjectionV1:
        return value
    return VerifiedColdH2ConfidenceRowProjectionV1(
        value.context_id,
        value.row_evidence_id,
        value.physical_evidence_id,
        value.support_epoch_id,
        value.confidence_snapshot_id,
        value.row_replay_verification_id,
        value.discovery_transcript_id,
        value.validation_transcript_id,
        value.validation_prefix_id,
        value.selected_checkpoint_draw_count,
        value.projection_id,
        value.projection_verification_id,
        value.state_semantic_id,
        value.remaining_horizon,
        value.action_semantic_id,
        value.discovery_support_descriptor_ids,
        value.validation_novel_descriptor_ids,
        value.interval_row,
        value.destinations,
        value.rank_cap,
        value.rank_profile,
        value.evidence_class,
        value.registered_target_evidence,
    )


@dataclass(frozen=True, slots=True, init=False)
class ObservationRelationalCoordinateV1:
    role: RelationalCoordinateRoleV1
    remaining_horizon: int
    _signature_bytes: bytes = field(repr=False)
    _signature_object: dict[str, Any] = field(repr=False, compare=False)
    _coordinate_id: str = field(init=False, repr=False)

    def __init__(
        self,
        role: RelationalCoordinateRoleV1,
        remaining_horizon: int,
        signature: Mapping[str, Any],
    ) -> None:
        if (
            type(role) is not RelationalCoordinateRoleV1
            or remaining_horizon not in (1, 2)
            or not isinstance(signature, Mapping)
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "relational coordinate is malformed"
            )
        try:
            encoded = canonical_json_bytes(dict(signature))
            decoded = loads_canonical_json(encoded)
        except (TypeError, ValueError) as error:
            raise V072ColdH2ModelBuilderInvariantViolation(
                f"coordinate signature is not canonical: {error}"
            ) from error
        if type(decoded) is not dict:
            raise V072ColdH2ModelBuilderInvariantViolation(
                "coordinate signature must be an object"
            )
        lowered_keys = {
            str(key).lower()
            for key in _all_mapping_keys(decoded)
        }
        if lowered_keys & FORBIDDEN_COORDINATE_KEYS:
            raise V072ColdH2ModelBuilderInvariantViolation(
                "coordinate leaks vertex/arm/source/D4/label identity"
            )
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "remaining_horizon", remaining_horizon)
        object.__setattr__(self, "_signature_bytes", encoded)
        object.__setattr__(self, "_signature_object", decoded)
        object.__setattr__(
            self,
            "_coordinate_id",
            _content_id("coordinate", self._payload()),
        )

    @property
    def signature(self) -> Mapping[str, Any]:
        return copy.deepcopy(self._signature_object)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_model_relational_coordinate.v1",
            "schema_version": SCHEMA_VERSION,
            "role": self.role.value,
            "remaining_horizon": self.remaining_horizon,
            "signature": self._signature_object,
            "derivation": COORDINATE_DERIVATION,
        }

    @property
    def coordinate_id(self) -> str:
        return self._coordinate_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "coordinate_id": self.coordinate_id}


def _all_mapping_keys(value: Any) -> tuple[str, ...]:
    keys: list[str] = []
    if isinstance(value, Mapping):
        for key, member in value.items():
            keys.append(str(key))
            keys.extend(_all_mapping_keys(member))
    elif isinstance(value, (tuple, list)):
        for member in value:
            keys.extend(_all_mapping_keys(member))
    return tuple(keys)


@dataclass(frozen=True, slots=True)
class ColdH2IntervalSimplexModelV1:
    context_id: str
    closure_id: str
    model_kind: ColdH2ModelKindV1
    root_state_id: str
    catalogues: tuple[robust.StateActionCatalogueV1, ...]
    destinations: tuple[robust.RegisteredDestinationV1, ...]
    rows: tuple[robust.IntervalSimplexRowV1, ...]
    concretizer_entries: tuple[
        robust.DistinctActionConcretizerEntryV1, ...
    ]
    physical_evidence_ids: tuple[str, ...]
    projection_binding_ids: tuple[str, ...]
    relational_context_id: str | None = None
    source_skeleton_id: str | None = None
    coordinate_profile_id: str | None = None
    bounded_refinement_status: str | None = None
    rank_cap: int = 4
    rank_profile: str = DEVELOPMENT_RANK_PROFILE
    row_bound_other: bool = True
    _model_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _validate_model(self)
        object.__setattr__(
            self,
            "_model_id",
            _content_id("model", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_cold_model_interval_simplex_model.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_id": self.context_id,
            "closure_id": self.closure_id,
            "model_kind": self.model_kind.value,
            "root_state_id": self.root_state_id,
            "catalogue_ids": [
                item.catalogue_id for item in self.catalogues
            ],
            "destination_entry_ids": [
                item.registry_entry_id for item in self.destinations
            ],
            "row_ids": [item.row_id for item in self.rows],
            "concretizer_entry_ids": [
                item.concretizer_entry_id
                for item in self.concretizer_entries
            ],
            "physical_evidence_ids": list(self.physical_evidence_ids),
            "projection_binding_ids": list(
                self.projection_binding_ids
            ),
            "relational_context_id": self.relational_context_id,
            "source_skeleton_id": self.source_skeleton_id,
            "coordinate_profile_id": self.coordinate_profile_id,
            "bounded_refinement_status": (
                self.bounded_refinement_status
            ),
            "rank_cap": self.rank_cap,
            "rank_profile": self.rank_profile,
            "row_bound_other": True,
            "kernel_calls": 0,
            "hidden_law_queries": 0,
            "source_prior_reads": 0,
        }

    @property
    def model_id(self) -> str:
        return self._model_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "catalogues": [item.to_document() for item in self.catalogues],
            "destinations": [
                item.to_document() for item in self.destinations
            ],
            "rows": [item.to_document() for item in self.rows],
            "concretizer_entries": [
                item.to_document() for item in self.concretizer_entries
            ],
            "model_id": self.model_id,
        }


def _validate_model(model: ColdH2IntervalSimplexModelV1) -> None:
    for value, label in (
        (model.context_id, "model context"),
        (model.closure_id, "model closure"),
        (model.root_state_id, "model root state"),
    ):
        _cid(value, label)
    if (
        type(model.model_kind) is not ColdH2ModelKindV1
        or type(model.catalogues) is not tuple
        or not model.catalogues
        or any(
            type(item) is not robust.StateActionCatalogueV1
            for item in model.catalogues
        )
        or tuple(item.state_id for item in model.catalogues)
        != tuple(sorted({item.state_id for item in model.catalogues}))
        or model.root_state_id
        not in {item.state_id for item in model.catalogues}
        or type(model.destinations) is not tuple
        or not model.destinations
        or any(
            type(item) is not robust.RegisteredDestinationV1
            for item in model.destinations
        )
        or tuple(item.destination_id for item in model.destinations)
        != tuple(
            sorted({item.destination_id for item in model.destinations})
        )
        or type(model.rows) is not tuple
        or not model.rows
        or any(
            type(item) is not robust.IntervalSimplexRowV1
            for item in model.rows
        )
        or tuple(item.row_id for item in model.rows)
        != tuple(sorted({item.row_id for item in model.rows}))
        or type(model.concretizer_entries) is not tuple
        or tuple(
            item.concretizer_entry_id
            for item in model.concretizer_entries
        )
        != tuple(
            sorted(
                {
                    item.concretizer_entry_id
                    for item in model.concretizer_entries
                }
            )
        )
        or model.physical_evidence_ids
        != tuple(sorted(set(model.physical_evidence_ids)))
        or model.projection_binding_ids
        != tuple(sorted(set(model.projection_binding_ids)))
        or len(model.physical_evidence_ids) != len(model.rows)
        or len(model.projection_binding_ids) != len(model.rows)
        or model.rank_cap != 4
        or model.rank_profile != DEVELOPMENT_RANK_PROFILE
        or model.row_bound_other is not True
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "cold interval model concrete registry is malformed"
        )
    catalogue_by_state = {
        item.state_id: item for item in model.catalogues
    }
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    row_by_key: dict[tuple[str, int, str], robust.IntervalSimplexRowV1] = {}
    for row in model.rows:
        catalogue = catalogue_by_state.get(row.state_id)
        if (
            catalogue is None
            or row.action_id
            not in {item.action_id for item in catalogue.actions}
            or row.row_key in row_by_key
            or any(
                item.destination_id not in destination_by_id
                for item in row.masses
            )
            or sum(
                destination_by_id[item.destination_id].category
                is robust.DestinationCategory.OTHER
                for item in row.masses
            )
            != 1
            or destination_by_id[row.other_destination_id].category
            is not robust.DestinationCategory.OTHER
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "model row is incomplete or loses row-bound OTHER"
            )
        row_by_key[row.row_key] = row
    required = {
        (
            catalogue.state_id,
            2 if catalogue.state_id == model.root_state_id else 1,
            action.action_id,
        )
        for catalogue in model.catalogues
        for action in catalogue.actions
    }
    if set(row_by_key) != required:
        raise V072ColdH2ModelBuilderInvariantViolation(
            "model rows do not cover every cold closure catalogue action"
        )
    for destination in model.destinations:
        if (
            destination.category is robust.DestinationCategory.ACTIVE_STATE
            and destination.state_id not in catalogue_by_state
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "active destination is outside the cold catalogue"
            )
    if model.model_kind is ColdH2ModelKindV1.GROUND_DIRECT:
        if (
            model.concretizer_entries
            or model.relational_context_id is not None
            or model.source_skeleton_id is not None
            or model.coordinate_profile_id is not None
            or model.bounded_refinement_status is not None
            or any(
                catalogue.state_coordinate_key != catalogue.state_id
                or any(
                    action.action_coordinate_key != action.action_id
                    for action in catalogue.actions
                )
                for catalogue in model.catalogues
            )
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "direct model changed ground state/action identity"
            )
    else:
        if (
            model.relational_context_id is None
            or model.source_skeleton_id != V0066_SOURCE_SKELETON_ID
            or model.coordinate_profile_id
            != V0068_BASE_COORDINATE_PROFILE_ID
            or model.bounded_refinement_status
            != BOUNDED_REFINEMENT_STATUS
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "quotient model lacks its frozen relational-program binding"
            )
        _cid(model.relational_context_id, "quotient relational context")
        action_by_state = {
            catalogue.state_id: {
                item.action_id: item for item in catalogue.actions
            }
            for catalogue in model.catalogues
        }
        covered: dict[str, set[str]] = {
            key: set() for key in action_by_state
        }
        for entry in model.concretizer_entries:
            catalogue = catalogue_by_state.get(entry.state_id)
            if (
                catalogue is None
                or entry.state_coordinate_key
                != catalogue.state_coordinate_key
            ):
                raise V072ColdH2ModelBuilderInvariantViolation(
                    "quotient concretizer has a stale state coordinate"
                )
            for action_id in entry.ground_action_ids:
                action = action_by_state[entry.state_id].get(action_id)
                if (
                    action is None
                    or action.action_coordinate_key
                    != entry.abstract_action_key
                    or action_id in covered[entry.state_id]
                ):
                    raise V072ColdH2ModelBuilderInvariantViolation(
                        "quotient concretizer is not distinct and complete"
                    )
                covered[entry.state_id].add(action_id)
        if any(
            covered[state_id] != set(actions)
            for state_id, actions in action_by_state.items()
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "quotient concretizer omits one ground action"
            )


def development_k4_threshold_profile_v1(
    context_id: str,
) -> robust.RobustThresholdProfileV1:
    return robust.RobustThresholdProfileV1(
        context_id,
        DEVELOPMENT_RISK_TOLERANCE,
        DEVELOPMENT_REWARD_CEILING,
    )


def _global_policy_abort_destination(
    context_id: str,
) -> robust.RegisteredDestinationV1:
    destination_id = _content_id(
        "global_other",
        {
            "schema": (
                "acfqp.v072_cold_model_absorbing_policy_abort_failure.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "semantic_role": "ABSORBING_POLICY_ABORT_FAILURE",
            "failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
        },
    )
    return robust.RegisteredDestinationV1(
        destination_id,
        robust.DestinationCategory.OTHER,
    )


@dataclass(frozen=True, slots=True)
class RowBoundOtherCollapseEntryV1:
    source_row_id: str
    source_other_destination_id: str
    source_other_mass_id: str
    planner_row_id: str
    planner_global_other_destination_id: str
    planner_other_mass_id: str
    preserved_non_other_mass_ids: tuple[str, ...]
    failure_value: int = 1
    continuation_reward_lower: Fraction = Fraction(0)
    _entry_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_row_id, "collapse source row"),
            (
                self.source_other_destination_id,
                "collapse source OTHER",
            ),
            (self.source_other_mass_id, "collapse source OTHER mass"),
            (self.planner_row_id, "collapse planner row"),
            (
                self.planner_global_other_destination_id,
                "collapse global OTHER",
            ),
            (self.planner_other_mass_id, "collapse planner OTHER mass"),
        ):
            _cid(value, label)
        if (
            self.preserved_non_other_mass_ids
            != tuple(sorted(set(self.preserved_non_other_mass_ids)))
            or any(
                _cid(value, "preserved non-OTHER mass") != value
                for value in self.preserved_non_other_mass_ids
            )
            or self.failure_value != 1
            or self.continuation_reward_lower != 0
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "row-bound OTHER collapse entry is unsound"
            )
        object.__setattr__(
            self,
            "_entry_id",
            _content_id("collapse_entry", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_cold_model_row_bound_other_collapse_entry.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_row_id": self.source_row_id,
            "source_other_destination_id": (
                self.source_other_destination_id
            ),
            "source_other_mass_id": self.source_other_mass_id,
            "planner_row_id": self.planner_row_id,
            "planner_global_other_destination_id": (
                self.planner_global_other_destination_id
            ),
            "planner_other_mass_id": self.planner_other_mass_id,
            "preserved_non_other_mass_ids": list(
                self.preserved_non_other_mass_ids
            ),
            "failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
            "mass_merging": False,
        }

    @property
    def entry_id(self) -> str:
        return self._entry_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "entry_id": self.entry_id}


@dataclass(frozen=True, slots=True)
class RowBoundOtherCollapseProofV1:
    context_id: str
    source_model_id: str
    planner_model_id: str
    global_other_destination_id: str
    entries: tuple[RowBoundOtherCollapseEntryV1, ...]
    source_row_count: int
    planner_row_count: int
    no_mass_merging: bool = True
    behavior_preserved: bool = True
    _proof_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.context_id, "collapse context"),
            (self.source_model_id, "collapse source model"),
            (self.planner_model_id, "collapse planner model"),
            (
                self.global_other_destination_id,
                "collapse global OTHER",
            ),
        ):
            _cid(value, label)
        if (
            type(self.entries) is not tuple
            or not self.entries
            or any(
                type(item) is not RowBoundOtherCollapseEntryV1
                for item in self.entries
            )
            or tuple(item.entry_id for item in self.entries)
            != tuple(sorted({item.entry_id for item in self.entries}))
            or self.source_row_count != len(self.entries)
            or self.planner_row_count != len(self.entries)
            or self.no_mass_merging is not True
            or self.behavior_preserved is not True
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "row-bound OTHER collapse proof is malformed"
            )
        object.__setattr__(
            self,
            "_proof_id",
            _content_id("collapse_proof", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_cold_model_row_bound_other_collapse_proof.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "source_model_id": self.source_model_id,
            "planner_model_id": self.planner_model_id,
            "global_other_destination_id": (
                self.global_other_destination_id
            ),
            "entry_ids": [item.entry_id for item in self.entries],
            "source_row_count": self.source_row_count,
            "planner_row_count": self.planner_row_count,
            "source_other_per_row": 1,
            "planner_other_per_row": 1,
            "failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
            "no_mass_merging": True,
            "behavior_preserved": True,
        }

    @property
    def proof_id(self) -> str:
        return self._proof_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "entries": [item.to_document() for item in self.entries],
            "proof_id": self.proof_id,
        }


@dataclass(frozen=True, slots=True)
class ColdH2PlannerProjectionV1:
    source_model: ColdH2IntervalSimplexModelV1
    planner_model: robust.PartialSupportIntervalModelV1
    collapse_proof: RowBoundOtherCollapseProofV1
    threshold_profile: robust.RobustThresholdProfileV1
    rank_cap: int = 4
    rank_profile: str = DEVELOPMENT_RANK_PROFILE
    _projection_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.source_model) is not ColdH2IntervalSimplexModelV1
            or type(self.planner_model)
            is not robust.PartialSupportIntervalModelV1
            or type(self.collapse_proof)
            is not RowBoundOtherCollapseProofV1
            or type(self.threshold_profile)
            is not robust.RobustThresholdProfileV1
            or self.collapse_proof.source_model_id
            != self.source_model.model_id
            or self.collapse_proof.planner_model_id
            != self.planner_model.model_id
            or self.planner_model.context_id
            != self.source_model.context_id
            or self.planner_model.root_state_id
            != self.source_model.root_state_id
            or self.threshold_profile.context_id
            != self.source_model.context_id
            or self.threshold_profile.risk_tolerance
            != DEVELOPMENT_RISK_TOLERANCE
            or self.threshold_profile.reward_ceiling
            != DEVELOPMENT_REWARD_CEILING
            or self.rank_cap != 4
            or self.rank_profile != DEVELOPMENT_RANK_PROFILE
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "planner projection or development threshold was transplanted"
            )
        object.__setattr__(
            self,
            "_projection_id",
            _content_id("planner_projection", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_model_planner_projection.v1",
            "schema_version": SCHEMA_VERSION,
            "source_model_id": self.source_model.model_id,
            "source_model_kind": self.source_model.model_kind.value,
            "planner_model_id": self.planner_model.model_id,
            "collapse_proof_id": self.collapse_proof.proof_id,
            "threshold_profile_id": (
                self.threshold_profile.threshold_profile_id
            ),
            "rank_cap": 4,
            "rank_profile": DEVELOPMENT_RANK_PROFILE,
            "registered_target_threshold_used": False,
        }

    @property
    def projection_id(self) -> str:
        return self._projection_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_model": self.source_model.to_document(),
            "planner_model": self.planner_model.to_document(),
            "collapse_proof": self.collapse_proof.to_document(),
            "threshold_profile": self.threshold_profile.to_document(),
            "projection_id": self.projection_id,
        }


def _project_to_legacy_planner_model(
    source_model: ColdH2IntervalSimplexModelV1,
    threshold_profile: robust.RobustThresholdProfileV1,
) -> ColdH2PlannerProjectionV1:
    global_other = _global_policy_abort_destination(
        source_model.context_id
    )
    source_destinations = {
        item.destination_id: item for item in source_model.destinations
    }
    non_other_destinations = tuple(
        item
        for item in source_model.destinations
        if item.category is not robust.DestinationCategory.OTHER
    )
    planner_rows: list[robust.IntervalSimplexRowV1] = []
    entries: list[RowBoundOtherCollapseEntryV1] = []
    for source_row in source_model.rows:
        source_other = source_destinations[
            source_row.other_destination_id
        ]
        if source_other.category is not robust.DestinationCategory.OTHER:
            raise V072ColdH2ModelBuilderInvariantViolation(
                "source row OTHER does not denote adversarial failure"
            )
        source_other_mass = source_row.other_mass
        planner_other_mass = robust.IntervalDestinationMassV1(
            global_other.destination_id,
            source_other_mass.lower,
            source_other_mass.upper,
        )
        preserved = tuple(
            mass
            for mass in source_row.masses
            if mass.destination_id != source_row.other_destination_id
        )
        planner_row = robust.IntervalSimplexRowV1(
            source_row.state_id,
            source_row.remaining_horizon,
            source_row.action_id,
            source_row.reward_lower,
            source_row.reward_upper,
            global_other.destination_id,
            tuple(
                sorted(
                    (*preserved, planner_other_mass),
                    key=lambda item: item.destination_id,
                )
            ),
        )
        planner_rows.append(planner_row)
        entries.append(
            RowBoundOtherCollapseEntryV1(
                source_row.row_id,
                source_row.other_destination_id,
                source_other_mass.mass_id,
                planner_row.row_id,
                global_other.destination_id,
                planner_other_mass.mass_id,
                tuple(sorted(item.mass_id for item in preserved)),
            )
        )
    planner_model = robust.build_partial_support_model_v1(
        context_id=source_model.context_id,
        root_state_id=source_model.root_state_id,
        catalogues=source_model.catalogues,
        destinations=(*non_other_destinations, global_other),
        rows=tuple(planner_rows),
        concretizer_entries=source_model.concretizer_entries,
    )
    proof = RowBoundOtherCollapseProofV1(
        source_model.context_id,
        source_model.model_id,
        planner_model.model_id,
        global_other.destination_id,
        tuple(sorted(entries, key=lambda item: item.entry_id)),
        len(source_model.rows),
        len(planner_model.rows),
    )
    return ColdH2PlannerProjectionV1(
        source_model,
        planner_model,
        proof,
        threshold_profile,
    )


@dataclass(frozen=True, slots=True)
class V072ColdH2ModelPairV1:
    closure_bundle: closure.V072ColdH2ClosureBundleV1
    row_projections: tuple[
        VerifiedColdH2ConfidenceRowProjectionV1, ...
    ]
    relational_context: ColdH2PublicRelationalContextV1
    relational_coordinates: tuple[
        ObservationRelationalCoordinateV1, ...
    ]
    direct_model: ColdH2IntervalSimplexModelV1
    quotient_model: ColdH2IntervalSimplexModelV1
    direct_planner_projection: ColdH2PlannerProjectionV1
    quotient_planner_projection: ColdH2PlannerProjectionV1
    threshold_profile: robust.RobustThresholdProfileV1
    shared_physical_row_ids: tuple[str, ...]
    shared_interval_row_ids: tuple[str, ...]
    _model_pair_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.closure_bundle)
            is not closure.V072ColdH2ClosureBundleV1
            or type(self.row_projections) is not tuple
            or any(
                type(item)
                is not VerifiedColdH2ConfidenceRowProjectionV1
                for item in self.row_projections
            )
            or type(self.relational_context)
            is not ColdH2PublicRelationalContextV1
            or self.relational_context.context_id
            != self.closure_bundle.context_id
            or type(self.relational_coordinates) is not tuple
            or any(
                type(item) is not ObservationRelationalCoordinateV1
                for item in self.relational_coordinates
            )
            or tuple(
                item.coordinate_id
                for item in self.relational_coordinates
            )
            != tuple(
                sorted(
                    {
                        item.coordinate_id
                        for item in self.relational_coordinates
                    }
                )
            )
            or type(self.direct_model) is not ColdH2IntervalSimplexModelV1
            or type(self.quotient_model)
            is not ColdH2IntervalSimplexModelV1
            or self.direct_model.model_kind
            is not ColdH2ModelKindV1.GROUND_DIRECT
            or self.quotient_model.model_kind
            is not (
                ColdH2ModelKindV1.OBSERVATION_RELATIONAL_QUOTIENT
            )
            or type(self.direct_planner_projection)
            is not ColdH2PlannerProjectionV1
            or type(self.quotient_planner_projection)
            is not ColdH2PlannerProjectionV1
            or self.direct_planner_projection.source_model
            != self.direct_model
            or self.quotient_planner_projection.source_model
            != self.quotient_model
            or type(self.threshold_profile)
            is not robust.RobustThresholdProfileV1
            or self.direct_planner_projection.threshold_profile
            != self.threshold_profile
            or self.quotient_planner_projection.threshold_profile
            != self.threshold_profile
            or self.direct_model.context_id
            != self.closure_bundle.context_id
            or self.quotient_model.context_id
            != self.closure_bundle.context_id
            or self.direct_model.closure_id
            != self.closure_bundle.closure_id
            or self.quotient_model.closure_id
            != self.closure_bundle.closure_id
            or self.quotient_model.relational_context_id
            != self.relational_context.relational_context_id
            or self.quotient_model.source_skeleton_id
            != self.relational_context.source_skeleton_id
            or self.quotient_model.coordinate_profile_id
            != self.relational_context.coordinate_profile_id
            or self.direct_model.rows != self.quotient_model.rows
            or self.shared_interval_row_ids
            != tuple(item.row_id for item in self.direct_model.rows)
            or self.shared_physical_row_ids
            != tuple(
                sorted(
                    item.physical_evidence_id
                    for item in self.row_projections
                )
            )
            or self.direct_model.physical_evidence_ids
            != self.shared_physical_row_ids
            or self.quotient_model.physical_evidence_ids
            != self.shared_physical_row_ids
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "direct/quotient models do not share one physical row inventory"
            )
        object.__setattr__(
            self,
            "_model_pair_id",
            _content_id("pair", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_cold_model_direct_quotient_pair.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "closure_id": self.closure_bundle.closure_id,
            "relational_context_id": (
                self.relational_context.relational_context_id
            ),
            "source_skeleton_id": (
                self.relational_context.source_skeleton_id
            ),
            "coordinate_profile_id": (
                self.relational_context.coordinate_profile_id
            ),
            "bounded_refinement_status": (
                self.relational_context.bounded_refinement_status
            ),
            "row_projection_binding_ids": [
                item.projection_binding_id
                for item in self.row_projections
            ],
            "relational_coordinate_ids": [
                item.coordinate_id
                for item in self.relational_coordinates
            ],
            "direct_model_id": self.direct_model.model_id,
            "quotient_model_id": self.quotient_model.model_id,
            "direct_planner_projection_id": (
                self.direct_planner_projection.projection_id
            ),
            "direct_planner_model_id": (
                self.direct_planner_projection.planner_model.model_id
            ),
            "quotient_planner_projection_id": (
                self.quotient_planner_projection.projection_id
            ),
            "quotient_planner_model_id": (
                self.quotient_planner_projection.planner_model.model_id
            ),
            "threshold_profile_id": (
                self.threshold_profile.threshold_profile_id
            ),
            "shared_physical_row_ids": list(
                self.shared_physical_row_ids
            ),
            "shared_interval_row_ids": list(
                self.shared_interval_row_ids
            ),
            "rank_cap": 4,
            "rank_profile": DEVELOPMENT_RANK_PROFILE,
            "registered_target_evidence": False,
            "kernel_calls": 0,
            "hidden_law_queries": 0,
            "source_prior_reads": 0,
        }

    @property
    def model_pair_id(self) -> str:
        return self._model_pair_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "relational_context": self.relational_context.to_document(),
            "row_projections": [
                item.to_document() for item in self.row_projections
            ],
            "relational_coordinates": [
                item.to_document()
                for item in self.relational_coordinates
            ],
            "direct_model": self.direct_model.to_document(),
            "quotient_model": self.quotient_model.to_document(),
            "direct_planner_model": (
                self.direct_planner_projection.planner_model.to_document()
            ),
            "quotient_planner_model": (
                self.quotient_planner_projection.planner_model.to_document()
            ),
            "model_pair_id": self.model_pair_id,
        }


@dataclass(frozen=True, slots=True)
class V072ColdH2GroundDirectSnapshotV1:
    """Direct-only immutable checkpoint; it contains no quotient artifacts."""

    closure_bundle: closure.V072ColdH2ClosureBundleV1
    row_projections: tuple[
        VerifiedColdH2ConfidenceRowProjectionV1, ...
    ]
    direct_model: ColdH2IntervalSimplexModelV1
    planner_projection: ColdH2PlannerProjectionV1
    threshold_profile: robust.RobustThresholdProfileV1
    _snapshot_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.closure_bundle)
            is not closure.V072ColdH2ClosureBundleV1
            or type(self.row_projections) is not tuple
            or not self.row_projections
            or any(
                type(item)
                is not VerifiedColdH2ConfidenceRowProjectionV1
                for item in self.row_projections
            )
            or self.direct_model.model_kind
            is not ColdH2ModelKindV1.GROUND_DIRECT
            or self.direct_model.concretizer_entries
            or self.direct_model.relational_context_id is not None
            or self.direct_model.source_skeleton_id is not None
            or self.direct_model.coordinate_profile_id is not None
            or self.planner_projection.source_model != self.direct_model
            or self.planner_projection.planner_model.concretizer_entries
            or self.threshold_profile != self.planner_projection.threshold_profile
            or self.threshold_profile.context_id
            != self.closure_bundle.context_id
            or self.direct_model.closure_id
            != self.closure_bundle.closure_id
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "direct-only checkpoint contains quotient or stale evidence"
            )
        object.__setattr__(
            self,
            "_snapshot_id",
            _content_id("direct_snapshot", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_cold_model_ground_direct_checkpoint_snapshot.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.closure_bundle.context_id,
            "closure_id": self.closure_bundle.closure_id,
            "direct_source_model_id": self.direct_model.model_id,
            "planner_projection_id": self.planner_projection.projection_id,
            "planner_model_id": (
                self.planner_projection.planner_model.model_id
            ),
            "collapse_proof_id": (
                self.planner_projection.collapse_proof.proof_id
            ),
            "threshold_profile_id": (
                self.threshold_profile.threshold_profile_id
            ),
            "checkpoint_rows": [
                {
                    "row_evidence_id": item.row_evidence_id,
                    "physical_evidence_id": item.physical_evidence_id,
                    "support_epoch_id": item.support_epoch_id,
                    "confidence_snapshot_id": item.confidence_snapshot_id,
                    "discovery_transcript_id": (
                        item.discovery_transcript_id
                    ),
                    "validation_transcript_id": (
                        item.validation_transcript_id
                    ),
                    "validation_prefix_id": item.validation_prefix_id,
                    "selected_checkpoint_draw_count": (
                        item.selected_checkpoint_draw_count
                    ),
                    "row_replay_verification_id": (
                        item.row_replay_verification_id
                    ),
                    "projection_binding_id": (
                        item.projection_binding_id
                    ),
                }
                for item in self.row_projections
            ],
            "relational_coordinates_built": 0,
            "concretizer_entries_built": 0,
            "source_skeleton_reads": 0,
            "source_prior_reads": 0,
        }

    @property
    def planner_model(self) -> robust.PartialSupportIntervalModelV1:
        return self.planner_projection.planner_model

    @property
    def collapse_proof(self) -> RowBoundOtherCollapseProofV1:
        return self.planner_projection.collapse_proof

    @property
    def snapshot_id(self) -> str:
        return self._snapshot_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_projections": [
                item.to_document() for item in self.row_projections
            ],
            "direct_model": self.direct_model.to_document(),
            "planner_projection": (
                self.planner_projection.to_document()
            ),
            "threshold_profile": self.threshold_profile.to_document(),
            "snapshot_id": self.snapshot_id,
        }


def _build_direct_source_materialization(
    *,
    closure_bundle: closure.V072ColdH2ClosureBundleV1,
    verified_row_projections: tuple[
        VerifiedConfidenceRowProjectionProtocolV1, ...
    ],
) -> tuple[
    tuple[VerifiedColdH2ConfidenceRowProjectionV1, ...],
    ColdH2IntervalSimplexModelV1,
]:
    if (
        type(closure_bundle) is not closure.V072ColdH2ClosureBundleV1
        or closure_bundle.cap_evidence.evidence_class
        is not (
            closure.ColdH2CapEvidenceClassV1
            .DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY
        )
        or type(verified_row_projections) is not tuple
        or not verified_row_projections
        or any(
            not isinstance(
                item, VerifiedConfidenceRowProjectionProtocolV1
            )
            for item in verified_row_projections
        )
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "builder requires exact development cold closure/projection inputs"
        )
    projections = tuple(
        sorted(
            (
                bind_verified_confidence_row_projection_v1(item)
                for item in verified_row_projections
            ),
            key=lambda item: item.projection_binding_id,
        )
    )
    rows_by_evidence = {
        item.row_evidence_id: item for item in closure_bundle.all_rows
    }
    projections_by_row = {
        item.row_evidence_id: item for item in projections
    }
    if (
        len(projections_by_row) != len(projections)
        or set(projections_by_row) != set(rows_by_evidence)
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "projection inventory is not one-to-one with closure rows"
        )
    catalogues = (
        (closure_bundle.root_catalogue,)
        + closure_bundle.child_catalogues
    )
    state_id_by_semantic = {
        catalogue.state.semantic_state_id: ground_state_id_v1(
            closure_bundle.context_id,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        for catalogue in catalogues
    }
    all_destinations: dict[str, robust.RegisteredDestinationV1] = {}
    interval_rows: list[robust.IntervalSimplexRowV1] = []
    for row_evidence_id, row in rows_by_evidence.items():
        item = projections_by_row[row_evidence_id]
        expected_state_id = state_id_by_semantic[
            row.state.semantic_state_id
        ]
        expected_action_id = ground_action_id_v1(
            row.context_id,
            row.state,
            row.remaining_horizon,
            row.action,
        )
        expected_destinations = tuple(
            sorted(
                (
                    *(
                        destination_for_descriptor_v1(row, member)
                        for member in row.discovery_support
                    ),
                    other_destination_for_row_v1(row),
                ),
                key=lambda member: member.destination_id,
            )
        )
        if (
            item.context_id != row.context_id
            or item.physical_evidence_id != row.physical_evidence_id
            or item.support_epoch_id != row.support_epoch_id
            or item.confidence_snapshot_id != row.confidence_snapshot_id
            or item.row_replay_verification_id
            != row.row_replay_verification_id
            or item.state_semantic_id
            != row.state.semantic_state_id
            or item.remaining_horizon != row.remaining_horizon
            or item.action_semantic_id
            != row.action.semantic_action_id
            or item.discovery_support_descriptor_ids
            != tuple(
                sorted(
                    member.descriptor_record_id
                    for member in row.discovery_support
                )
            )
            or item.validation_novel_descriptor_ids
            != tuple(
                sorted(
                    member.descriptor_record_id
                    for member in row.validation_novel
                )
            )
            or item.interval_row.state_id != expected_state_id
            or item.interval_row.action_id != expected_action_id
            or item.destinations != expected_destinations
            or item.interval_row.other_destination_id
            != row_bound_other_destination_id_v1(row)
            or item.interval_row.reward_upper
            > DEVELOPMENT_REWARD_CEILING
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "verified projection was transplanted or changes public row semantics"
            )
        for destination in item.destinations:
            previous = all_destinations.setdefault(
                destination.destination_id, destination
            )
            if previous != destination:
                raise V072ColdH2ModelBuilderInvariantViolation(
                    "one destination ID has conflicting registry semantics"
                )
        interval_rows.append(item.interval_row)
    direct_catalogues = tuple(
        sorted(
            (
                robust.StateActionCatalogueV1(
                    state_id_by_semantic[
                        catalogue.state.semantic_state_id
                    ],
                    state_id_by_semantic[
                        catalogue.state.semantic_state_id
                    ],
                    tuple(
                        sorted(
                            (
                                robust.CatalogueActionV1(
                                    action_id,
                                    action_id,
                                )
                                for action in catalogue.actions
                                for action_id in (
                                    ground_action_id_v1(
                                        closure_bundle.context_id,
                                        catalogue.state,
                                        catalogue.remaining_horizon,
                                        action,
                                    ),
                                )
                            ),
                            key=lambda item: item.action_id,
                        )
                    ),
                )
                for catalogue in catalogues
            ),
            key=lambda item: item.state_id,
        )
    )
    rows = tuple(sorted(interval_rows, key=lambda item: item.row_id))
    destinations = tuple(
        sorted(
            all_destinations.values(),
            key=lambda item: item.destination_id,
        )
    )
    physical_ids = tuple(
        sorted(item.physical_evidence_id for item in projections)
    )
    projection_ids = tuple(
        sorted(item.projection_binding_id for item in projections)
    )
    root_state_id = state_id_by_semantic[
        closure_bundle.root_state.semantic_state_id
    ]
    return projections, ColdH2IntervalSimplexModelV1(
        closure_bundle.context_id,
        closure_bundle.closure_id,
        ColdH2ModelKindV1.GROUND_DIRECT,
        root_state_id,
        direct_catalogues,
        destinations,
        rows,
        (),
        physical_ids,
        projection_ids,
    )


def build_v072_cold_h2_ground_direct_model_v1(
    *,
    closure_bundle: closure.V072ColdH2ClosureBundleV1,
    verified_row_projections: tuple[
        VerifiedConfidenceRowProjectionProtocolV1, ...
    ],
) -> V072ColdH2GroundDirectSnapshotV1:
    """Build only the ground-direct checkpoint and standard planner model."""

    projections, direct_model = _build_direct_source_materialization(
        closure_bundle=closure_bundle,
        verified_row_projections=verified_row_projections,
    )
    threshold = development_k4_threshold_profile_v1(
        closure_bundle.context_id
    )
    planner_projection = _project_to_legacy_planner_model(
        direct_model, threshold
    )
    return V072ColdH2GroundDirectSnapshotV1(
        closure_bundle,
        projections,
        direct_model,
        planner_projection,
        threshold,
    )


def _base_coordinate_signature(
    *,
    program: str,
    value: int,
) -> dict[str, Any]:
    return {
        "portable_base_program": program,
        "portable_base_value": value,
        "bounded_refinement": {
            "kind": "NOT_APPLICABLE",
            "status": BOUNDED_REFINEMENT_STATUS,
            "values": [],
        },
        "sample_independent": True,
    }


def build_v072_cold_h2_models_v1(
    *,
    closure_bundle: closure.V072ColdH2ClosureBundleV1,
    verified_row_projections: tuple[
        VerifiedConfidenceRowProjectionProtocolV1, ...
    ],
    relational_context: ColdH2PublicRelationalContextV1,
) -> V072ColdH2ModelPairV1:
    """Build direct and sample-independent relational quotient views."""

    direct_snapshot = build_v072_cold_h2_ground_direct_model_v1(
        closure_bundle=closure_bundle,
        verified_row_projections=verified_row_projections,
    )
    if (
        type(relational_context) is not ColdH2PublicRelationalContextV1
        or relational_context.context_id != closure_bundle.context_id
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "relational context is absent or transplanted"
        )
    direct_model = direct_snapshot.direct_model
    source_catalogues = (
        (closure_bundle.root_catalogue,)
        + closure_bundle.child_catalogues
    )
    direct_by_state = {
        item.state_id: item for item in direct_model.catalogues
    }
    state_coordinates: dict[str, ObservationRelationalCoordinateV1] = {}
    action_coordinates: dict[
        tuple[str, str], ObservationRelationalCoordinateV1
    ] = {}
    support_coordinates: dict[
        tuple[str, str], ObservationRelationalCoordinateV1
    ] = {}
    for source_catalogue in source_catalogues:
        state_id = ground_state_id_v1(
            closure_bundle.context_id,
            source_catalogue.state,
            source_catalogue.remaining_horizon,
        )
        direct_catalogue = direct_by_state[state_id]
        state_value, action_value_by_record = (
            _replay_catalogue_relational_values(
                relational_context, source_catalogue
            )
        )
        state_coordinates[state_id] = ObservationRelationalCoordinateV1(
            RelationalCoordinateRoleV1.STATE,
            source_catalogue.remaining_horizon,
            _base_coordinate_signature(
                program="cardinality_actions(legal_actions)",
                value=state_value,
            ),
        )
        source_action_by_ground_id = {
            ground_action_id_v1(
                closure_bundle.context_id,
                source_catalogue.state,
                source_catalogue.remaining_horizon,
                action,
            ): action
            for action in source_catalogue.actions
        }
        if set(source_action_by_ground_id) != {
            item.action_id for item in direct_catalogue.actions
        }:
            raise V072ColdH2ModelBuilderInvariantViolation(
                "ground action identity differs from public catalogue"
            )
        for ground_action in direct_catalogue.actions:
            source_action = source_action_by_ground_id[
                ground_action.action_id
            ]
            action_value = action_value_by_record[
                source_action.action_record_id
            ]
            action_coordinates[
                (state_id, ground_action.action_id)
            ] = ObservationRelationalCoordinateV1(
                RelationalCoordinateRoleV1.ACTION,
                source_catalogue.remaining_horizon,
                _base_coordinate_signature(
                    program=(
                        "cardinality_resources("
                        "linked_filter(action_anchor,active_resources))"
                    ),
                    value=action_value,
                ),
            )
            support_coordinates[
                (state_id, ground_action.action_id)
            ] = ObservationRelationalCoordinateV1(
                RelationalCoordinateRoleV1.SUPPORT,
                source_catalogue.remaining_horizon,
                {
                    "portable_support_tuple": [
                        source_catalogue.remaining_horizon,
                        state_value,
                        action_value,
                    ],
                    "bounded_refinement": {
                        "kind": "NOT_APPLICABLE",
                        "status": BOUNDED_REFINEMENT_STATUS,
                        "values": [],
                    },
                    "sample_independent": True,
                },
            )
    quotient_catalogues: list[robust.StateActionCatalogueV1] = []
    concretizers: list[robust.DistinctActionConcretizerEntryV1] = []
    for direct_catalogue in direct_model.catalogues:
        state_coordinate = state_coordinates[direct_catalogue.state_id]
        actions = tuple(
            robust.CatalogueActionV1(
                item.action_id,
                action_coordinates[
                    (direct_catalogue.state_id, item.action_id)
                ].coordinate_id,
            )
            for item in direct_catalogue.actions
        )
        quotient_catalogue = robust.StateActionCatalogueV1(
            direct_catalogue.state_id,
            state_coordinate.coordinate_id,
            actions,
        )
        quotient_catalogues.append(quotient_catalogue)
        grouped: dict[str, list[str]] = {}
        for action in actions:
            grouped.setdefault(
                action.action_coordinate_key, []
            ).append(action.action_id)
        concretizers.extend(
            robust.DistinctActionConcretizerEntryV1(
                quotient_catalogue.state_coordinate_key,
                quotient_catalogue.state_id,
                coordinate,
                tuple(sorted(action_ids)),
            )
            for coordinate, action_ids in grouped.items()
        )
    quotient_catalogue_tuple = tuple(
        sorted(quotient_catalogues, key=lambda item: item.state_id)
    )
    concretizer_tuple = tuple(
        sorted(
            concretizers,
            key=lambda item: item.concretizer_entry_id,
        )
    )
    coordinate_by_id = {
        item.coordinate_id: item
        for item in (
            *state_coordinates.values(),
            *action_coordinates.values(),
            *support_coordinates.values(),
        )
    }
    coordinate_tuple = tuple(
        sorted(
            coordinate_by_id.values(),
            key=lambda item: item.coordinate_id,
        )
    )
    quotient_model = ColdH2IntervalSimplexModelV1(
        closure_bundle.context_id,
        closure_bundle.closure_id,
        ColdH2ModelKindV1.OBSERVATION_RELATIONAL_QUOTIENT,
        direct_model.root_state_id,
        quotient_catalogue_tuple,
        direct_model.destinations,
        direct_model.rows,
        concretizer_tuple,
        direct_model.physical_evidence_ids,
        direct_model.projection_binding_ids,
        relational_context.relational_context_id,
        relational_context.source_skeleton_id,
        relational_context.coordinate_profile_id,
        relational_context.bounded_refinement_status,
    )
    quotient_projection = _project_to_legacy_planner_model(
        quotient_model,
        direct_snapshot.threshold_profile,
    )
    return V072ColdH2ModelPairV1(
        closure_bundle,
        direct_snapshot.row_projections,
        relational_context,
        coordinate_tuple,
        direct_model,
        quotient_model,
        direct_snapshot.planner_projection,
        quotient_projection,
        direct_snapshot.threshold_profile,
        direct_model.physical_evidence_ids,
        tuple(item.row_id for item in direct_model.rows),
    )


@dataclass(frozen=True, slots=True)
class RegisteredColdH2PublicRelationalContextV1:
    """Exact rank-cap-6 public topology for source-frozen coordinate replay."""

    context_id: str
    topology_id: str
    vertex_count: int
    edges: tuple[tuple[int, int], ...]
    rank_cap: int = prereg.RANK_CAP
    source_skeleton_id: str = V0066_SOURCE_SKELETON_ID
    state_program_id: str = V0066_STATE_PROGRAM_ID
    action_program_id: str = V0066_ACTION_PROGRAM_ID
    coordinate_profile_id: str = V0068_BASE_COORDINATE_PROFILE_ID
    bounded_refinement_status: str = BOUNDED_REFINEMENT_STATUS
    _relational_context_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        registered = next(
            (
                item
                for item in prereg.registered_heldout_public_contexts_v2()
                if item.context_id == self.context_id
            ),
            None,
        )
        for value, label in (
            (self.context_id, "registered relational context"),
            (self.topology_id, "registered public topology"),
            (self.source_skeleton_id, "registered source skeleton"),
            (self.state_program_id, "registered state program"),
            (self.action_program_id, "registered action program"),
            (
                self.coordinate_profile_id,
                "registered coordinate profile",
            ),
        ):
            _cid(value, label)
        if (
            type(registered)
            is not prereg.HeldoutPublicGraphContextV2
            or self.topology_id != registered.topology.topology_id
            or self.vertex_count != registered.topology.vertex_count
            or self.edges != registered.topology.edges
            or self.rank_cap != prereg.RANK_CAP
            or self.source_skeleton_id != V0066_SOURCE_SKELETON_ID
            or self.state_program_id != V0066_STATE_PROGRAM_ID
            or self.action_program_id != V0066_ACTION_PROGRAM_ID
            or self.coordinate_profile_id
            != V0068_BASE_COORDINATE_PROFILE_ID
            or self.bounded_refinement_status
            != BOUNDED_REFINEMENT_STATUS
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered relational context is not one exact public "
                "confirmatory topology"
            )
        object.__setattr__(
            self,
            "_relational_context_id",
            _content_id(
                "registered_relational_context",
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_cold_h2_relational_context.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "topology_id": self.topology_id,
            "vertex_count": self.vertex_count,
            "edges": [list(edge) for edge in self.edges],
            "rank_cap": prereg.RANK_CAP,
            "source_skeleton_id": self.source_skeleton_id,
            "state_program_id": self.state_program_id,
            "action_program_id": self.action_program_id,
            "coordinate_profile_id": self.coordinate_profile_id,
            "bounded_refinement_status": self.bounded_refinement_status,
            "public_semantics_only": True,
            "source_observation_rows_imported": False,
            "source_feature_ranks_imported": False,
            "registered_target_evidence": True,
        }

    @property
    def relational_context_id(self) -> str:
        return self._relational_context_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "relational_context_id": self.relational_context_id,
        }


def registered_cold_h2_relational_context_v1(
    context: prereg.HeldoutPublicGraphContextV2,
) -> RegisteredColdH2PublicRelationalContextV1:
    if (
        type(context) is not prereg.HeldoutPublicGraphContextV2
        or context not in prereg.registered_heldout_public_contexts_v2()
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "registered relational context factory requires one exact "
            "confirmatory public context"
        )
    return RegisteredColdH2PublicRelationalContextV1(
        context.context_id,
        context.topology.topology_id,
        context.topology.vertex_count,
        context.topology.edges,
    )


def _registered_replay_catalogue_relational_values(
    relational_context: RegisteredColdH2PublicRelationalContextV1,
    catalogue: closure.ColdPublicCatalogueV1,
) -> tuple[int, dict[str, int]]:
    if (
        type(relational_context)
        is not RegisteredColdH2PublicRelationalContextV1
        or type(catalogue) is not closure.ColdPublicCatalogueV1
        or catalogue.context_id != relational_context.context_id
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "registered coordinate replay requires exact public inputs"
        )
    state_document = dict(catalogue.state.document)
    ranks = state_document.get("ranks")
    if (
        state_document.get("topology_id")
        != relational_context.topology_id
        or type(ranks) is not list
        or len(ranks) != relational_context.vertex_count
        or any(
            type(rank) is not int
            or not 0 <= rank <= relational_context.rank_cap
            for rank in ranks
        )
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "registered state lacks exact public rank/topology semantics"
        )
    expected_actions = tuple(
        sorted(
            (first, second, survivor)
            for first, second in relational_context.edges
            if ranks[first] > 0 and ranks[first] == ranks[second]
            for survivor in (first, second)
        )
    )
    actual: dict[str, tuple[int, int, int]] = {}
    for action in catalogue.actions:
        document = dict(action.document)
        raw = document.get("action")
        if (
            document.get("context_id") != relational_context.context_id
            or document.get("topology_id")
            != relational_context.topology_id
            or type(raw) is not list
            or len(raw) != 3
            or any(type(item) is not int for item in raw)
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered action lacks exact public semantics"
            )
        triple = tuple(raw)
        if (
            tuple(sorted(triple[:2])) not in relational_context.edges
            or triple[2] not in triple[:2]
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered action is outside the public topology"
            )
        actual[action.action_record_id] = triple
    if (
        tuple(sorted(actual.values())) != expected_actions
        or len(actual) != len(expected_actions)
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "registered catalogue is not the complete public action set"
        )
    active = {
        vertex for vertex, rank in enumerate(ranks) if rank > 0
    }
    neighbours = {
        vertex: set()
        for vertex in range(relational_context.vertex_count)
    }
    for first, second in relational_context.edges:
        neighbours[first].add(second)
        neighbours[second].add(first)
    return len(expected_actions), {
        record_id: len(neighbours[action[2]] & active)
        for record_id, action in actual.items()
    }


def replay_registered_base_coordinate_values_v1(
    relational_context: RegisteredColdH2PublicRelationalContextV1,
    catalogue: closure.ColdPublicCatalogueV1,
) -> tuple[int, tuple[tuple[str, int], ...]]:
    """Pure public replay; it opens no observer and uses no target evidence."""

    state_value, action_values = (
        _registered_replay_catalogue_relational_values(
            relational_context,
            catalogue,
        )
    )
    return state_value, tuple(sorted(action_values.items()))


_REGISTERED_MODEL_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredColdH2IntervalSimplexModelV1:
    _minting_capability: object
    context_id: str
    closure_id: str
    model_kind: ColdH2ModelKindV1
    root_state_id: str
    catalogues: tuple[robust.StateActionCatalogueV1, ...]
    destinations: tuple[robust.RegisteredDestinationV1, ...]
    rows: tuple[robust.IntervalSimplexRowV1, ...]
    concretizer_entries: tuple[
        robust.DistinctActionConcretizerEntryV1, ...
    ]
    physical_evidence_ids: tuple[str, ...]
    projection_ids: tuple[str, ...]
    relational_context_id: str | None
    rank_cap: int = prereg.RANK_CAP
    rank_profile: str = PRODUCTION_RANK_PROFILE
    _model_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.context_id, "registered model context"),
            (self.closure_id, "registered model closure"),
            (self.root_state_id, "registered model root"),
        ):
            _cid(value, label)
        if self.relational_context_id is not None:
            _cid(
                self.relational_context_id,
                "registered model relational context",
            )
        if (
            self._minting_capability
            is not _REGISTERED_MODEL_MINTING_SENTINEL
            or type(self.model_kind) is not ColdH2ModelKindV1
            or type(self.catalogues) is not tuple
            or not self.catalogues
            or any(
                type(item) is not robust.StateActionCatalogueV1
                for item in self.catalogues
            )
            or tuple(item.state_id for item in self.catalogues)
            != tuple(sorted({item.state_id for item in self.catalogues}))
            or self.root_state_id
            not in {item.state_id for item in self.catalogues}
            or type(self.destinations) is not tuple
            or not self.destinations
            or any(
                type(item) is not robust.RegisteredDestinationV1
                for item in self.destinations
            )
            or tuple(item.destination_id for item in self.destinations)
            != tuple(
                sorted({item.destination_id for item in self.destinations})
            )
            or type(self.rows) is not tuple
            or not self.rows
            or any(
                type(item) is not robust.IntervalSimplexRowV1
                for item in self.rows
            )
            or tuple(item.row_id for item in self.rows)
            != tuple(sorted({item.row_id for item in self.rows}))
            or type(self.concretizer_entries) is not tuple
            or tuple(
                item.concretizer_entry_id
                for item in self.concretizer_entries
            )
            != tuple(
                sorted(
                    {
                        item.concretizer_entry_id
                        for item in self.concretizer_entries
                    }
                )
            )
            or self.physical_evidence_ids
            != tuple(sorted(set(self.physical_evidence_ids)))
            or self.projection_ids
            != tuple(sorted(set(self.projection_ids)))
            or len(self.physical_evidence_ids) != len(self.rows)
            or len(self.projection_ids) != len(self.rows)
            or self.rank_cap != prereg.RANK_CAP
            or self.rank_profile != PRODUCTION_RANK_PROFILE
            or (
                self.model_kind is ColdH2ModelKindV1.GROUND_DIRECT
                and (
                    self.concretizer_entries
                    or self.relational_context_id is not None
                )
            )
            or (
                self.model_kind
                is ColdH2ModelKindV1.OBSERVATION_RELATIONAL_QUOTIENT
                and (
                    not self.concretizer_entries
                    or self.relational_context_id is None
                )
            )
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered cold H2 model registry is malformed"
            )
        catalogue_by_state = {
            item.state_id: item for item in self.catalogues
        }
        destination_by_id = {
            item.destination_id: item for item in self.destinations
        }
        row_keys: set[tuple[str, int, str]] = set()
        for row in self.rows:
            catalogue = catalogue_by_state.get(row.state_id)
            if (
                catalogue is None
                or row.action_id
                not in {
                    item.action_id for item in catalogue.actions
                }
                or row.row_key in row_keys
                or any(
                    mass.destination_id not in destination_by_id
                    for mass in row.masses
                )
                or destination_by_id[
                    row.other_destination_id
                ].category
                is not robust.DestinationCategory.OTHER
                or row.reward_upper > PRODUCTION_REWARD_CEILING
            ):
                raise V072ColdH2ModelBuilderInvariantViolation(
                    "registered row is missing, transplanted, or exceeds "
                    "the frozen production reward ceiling"
                )
            row_keys.add(row.row_key)
        required = {
            (
                catalogue.state_id,
                (
                    2
                    if catalogue.state_id == self.root_state_id
                    else 1
                ),
                action.action_id,
            )
            for catalogue in self.catalogues
            for action in catalogue.actions
        }
        if row_keys != required:
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered model does not cover every physical row once"
            )
        object.__setattr__(
            self,
            "_model_id",
            _content_id("registered_model", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_cold_h2_model.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "closure_id": self.closure_id,
            "model_kind": self.model_kind.value,
            "root_state_id": self.root_state_id,
            "catalogue_ids": [
                item.catalogue_id for item in self.catalogues
            ],
            "destination_entry_ids": [
                item.registry_entry_id for item in self.destinations
            ],
            "row_ids": [item.row_id for item in self.rows],
            "concretizer_entry_ids": [
                item.concretizer_entry_id
                for item in self.concretizer_entries
            ],
            "physical_evidence_ids": list(self.physical_evidence_ids),
            "registered_projection_ids": list(self.projection_ids),
            "relational_context_id": self.relational_context_id,
            "rank_cap": prereg.RANK_CAP,
            "rank_profile": PRODUCTION_RANK_PROFILE,
            "registered_target_evidence": True,
            "independent_model_replay_status": (
                REGISTERED_TARGET_MODEL_INDEPENDENT_REPLAY_STATUS
            ),
            "kernel_calls": 0,
            "hidden_law_queries": 0,
            "source_prior_reads": 0,
        }

    @property
    def model_id(self) -> str:
        return self._model_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "catalogues": [
                item.to_document() for item in self.catalogues
            ],
            "destinations": [
                item.to_document() for item in self.destinations
            ],
            "rows": [item.to_document() for item in self.rows],
            "concretizer_entries": [
                item.to_document() for item in self.concretizer_entries
            ],
            "model_id": self.model_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredRowBoundOtherCollapseProofV1:
    source_model_id: str
    planner_model_id: str
    global_other_destination_id: str
    row_mappings: tuple[tuple[str, str, str], ...]
    _proof_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_model_id, "registered collapse source"),
            (self.planner_model_id, "registered collapse planner"),
            (
                self.global_other_destination_id,
                "registered collapse global OTHER",
            ),
        ):
            _cid(value, label)
        if (
            type(self.row_mappings) is not tuple
            or not self.row_mappings
            or self.row_mappings
            != tuple(sorted(set(self.row_mappings)))
            or any(
                type(item) is not tuple
                or len(item) != 3
                or any(
                    _cid(value, "registered collapse mapping") != value
                    for value in item
                )
                for item in self.row_mappings
            )
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered row-bound OTHER collapse proof is malformed"
            )
        object.__setattr__(
            self,
            "_proof_id",
            _content_id("registered_collapse", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_cold_h2_other_collapse_proof.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "source_model_id": self.source_model_id,
            "planner_model_id": self.planner_model_id,
            "global_other_destination_id": (
                self.global_other_destination_id
            ),
            "row_mappings": [list(item) for item in self.row_mappings],
            "row_bound_other_per_source_row": 1,
            "global_other_in_planner": True,
            "failure_value": 1,
            "continuation_reward_lower": _fdoc(Fraction(0)),
            "mass_merging": False,
        }

    @property
    def proof_id(self) -> str:
        return self._proof_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proof_id": self.proof_id}


def _registered_global_other_destination(
    context_id: str,
) -> robust.RegisteredDestinationV1:
    return robust.RegisteredDestinationV1(
        _content_id(
            "registered_global_other",
            {
                "schema": (
                    "acfqp.v072_registered_cold_h2_global_other.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "context_id": context_id,
                "failure_value": 1,
                "continuation_reward_lower": _fdoc(Fraction(0)),
            },
        ),
        robust.DestinationCategory.OTHER,
    )


def _registered_planner_projection(
    source_model: RegisteredColdH2IntervalSimplexModelV1,
) -> tuple[
    robust.PartialSupportIntervalModelV1,
    RegisteredRowBoundOtherCollapseProofV1,
]:
    global_other = _registered_global_other_destination(
        source_model.context_id
    )
    destination_by_id = {
        item.destination_id: item for item in source_model.destinations
    }
    non_other = tuple(
        item
        for item in source_model.destinations
        if item.category is not robust.DestinationCategory.OTHER
    )
    rows: list[robust.IntervalSimplexRowV1] = []
    mappings: list[tuple[str, str, str]] = []
    for source_row in source_model.rows:
        source_other = destination_by_id[
            source_row.other_destination_id
        ]
        if source_other.category is not robust.DestinationCategory.OTHER:
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered source OTHER is not adversarial"
            )
        planner_other_mass = robust.IntervalDestinationMassV1(
            global_other.destination_id,
            source_row.other_mass.lower,
            source_row.other_mass.upper,
        )
        planner_row = robust.IntervalSimplexRowV1(
            source_row.state_id,
            source_row.remaining_horizon,
            source_row.action_id,
            source_row.reward_lower,
            source_row.reward_upper,
            global_other.destination_id,
            tuple(
                sorted(
                    (
                        *(
                            mass
                            for mass in source_row.masses
                            if mass.destination_id
                            != source_row.other_destination_id
                        ),
                        planner_other_mass,
                    ),
                    key=lambda item: item.destination_id,
                )
            ),
        )
        rows.append(planner_row)
        mappings.append(
            (
                source_row.row_id,
                source_row.other_destination_id,
                planner_row.row_id,
            )
        )
    planner = robust.build_partial_support_model_v1(
        context_id=source_model.context_id,
        root_state_id=source_model.root_state_id,
        catalogues=source_model.catalogues,
        destinations=(*non_other, global_other),
        rows=tuple(rows),
        concretizer_entries=source_model.concretizer_entries,
    )
    proof = RegisteredRowBoundOtherCollapseProofV1(
        source_model.model_id,
        planner.model_id,
        global_other.destination_id,
        tuple(sorted(mappings)),
    )
    return planner, proof


_REGISTERED_PAIR_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredColdH2ModelPairV1:
    _minting_capability: object
    anchor_id: str
    final_preregistration_id: str
    closure_bundle: closure.V072ColdH2ClosureBundleV1
    row_projections: tuple[
        row_projection.RegisteredConfidenceIntervalSimplexRowProjectionV1,
        ...,
    ]
    relational_context: RegisteredColdH2PublicRelationalContextV1
    relational_coordinates: tuple[ObservationRelationalCoordinateV1, ...]
    direct_model: RegisteredColdH2IntervalSimplexModelV1
    quotient_model: RegisteredColdH2IntervalSimplexModelV1
    direct_planner_model: robust.PartialSupportIntervalModelV1
    quotient_planner_model: robust.PartialSupportIntervalModelV1
    direct_collapse_proof: RegisteredRowBoundOtherCollapseProofV1
    quotient_collapse_proof: RegisteredRowBoundOtherCollapseProofV1
    threshold_profile: robust.RobustThresholdProfileV1
    independent_model_replay_attestation_id: None = None
    _model_pair_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.anchor_id, "registered pair anchor")
        _cid(
            self.final_preregistration_id,
            "registered pair final preregistration",
        )
        if (
            self._minting_capability
            is not _REGISTERED_PAIR_MINTING_SENTINEL
            or type(self.closure_bundle)
            is not closure.V072ColdH2ClosureBundleV1
            or self.closure_bundle.cap_evidence.evidence_class
            is not closure.ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED
            or type(self.row_projections) is not tuple
            or not self.row_projections
            or any(
                type(item)
                is not (
                    row_projection
                    .RegisteredConfidenceIntervalSimplexRowProjectionV1
                )
                for item in self.row_projections
            )
            or type(self.relational_context)
            is not RegisteredColdH2PublicRelationalContextV1
            or type(self.direct_model)
            is not RegisteredColdH2IntervalSimplexModelV1
            or type(self.quotient_model)
            is not RegisteredColdH2IntervalSimplexModelV1
            or self.direct_model.model_kind
            is not ColdH2ModelKindV1.GROUND_DIRECT
            or self.quotient_model.model_kind
            is not ColdH2ModelKindV1.OBSERVATION_RELATIONAL_QUOTIENT
            or self.direct_model.rows != self.quotient_model.rows
            or self.direct_model.physical_evidence_ids
            != self.quotient_model.physical_evidence_ids
            or self.direct_model.projection_ids
            != self.quotient_model.projection_ids
            or self.direct_collapse_proof.source_model_id
            != self.direct_model.model_id
            or self.direct_collapse_proof.planner_model_id
            != self.direct_planner_model.model_id
            or self.quotient_collapse_proof.source_model_id
            != self.quotient_model.model_id
            or self.quotient_collapse_proof.planner_model_id
            != self.quotient_planner_model.model_id
            or self.threshold_profile.context_id
            != self.closure_bundle.context_id
            or self.threshold_profile.risk_tolerance
            != PRODUCTION_RISK_TOLERANCE
            or self.threshold_profile.reward_ceiling
            != PRODUCTION_REWARD_CEILING
            or self.independent_model_replay_attestation_id is not None
            or self.relational_context.context_id
            != self.closure_bundle.context_id
            or self.direct_model.context_id
            != self.closure_bundle.context_id
            or self.quotient_model.context_id
            != self.closure_bundle.context_id
            or self.direct_model.closure_id
            != self.closure_bundle.closure_id
            or self.quotient_model.closure_id
            != self.closure_bundle.closure_id
            or self.quotient_model.relational_context_id
            != self.relational_context.relational_context_id
            or any(
                item.confidence_authority.anchor_id != self.anchor_id
                or item.confidence_authority.final_preregistration_id
                != self.final_preregistration_id
                for item in self.row_projections
            )
            or {
                item.row_evidence_id for item in self.row_projections
            }
            != {
                item.row_evidence_id
                for item in self.closure_bundle.all_rows
            }
            or self.direct_planner_model.context_id
            != self.closure_bundle.context_id
            or self.quotient_planner_model.context_id
            != self.closure_bundle.context_id
            or self.direct_planner_model.root_state_id
            != self.direct_model.root_state_id
            or self.quotient_planner_model.root_state_id
            != self.quotient_model.root_state_id
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered direct/quotient pair is stale or mixes "
                "development/target evidence"
            )
        object.__setattr__(
            self,
            "_model_pair_id",
            _content_id("registered_pair", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_cold_h2_direct_quotient_pair.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "final_preregistration_id": self.final_preregistration_id,
            "closure_id": self.closure_bundle.closure_id,
            "registered_projection_ids": [
                item.projection_id for item in self.row_projections
            ],
            "relational_context_id": (
                self.relational_context.relational_context_id
            ),
            "relational_coordinate_ids": [
                item.coordinate_id
                for item in self.relational_coordinates
            ],
            "direct_model_id": self.direct_model.model_id,
            "quotient_model_id": self.quotient_model.model_id,
            "direct_planner_model_id": self.direct_planner_model.model_id,
            "quotient_planner_model_id": (
                self.quotient_planner_model.model_id
            ),
            "direct_collapse_proof_id": (
                self.direct_collapse_proof.proof_id
            ),
            "quotient_collapse_proof_id": (
                self.quotient_collapse_proof.proof_id
            ),
            "threshold_profile_id": (
                self.threshold_profile.threshold_profile_id
            ),
            "rank_cap": prereg.RANK_CAP,
            "rank_profile": PRODUCTION_RANK_PROFILE,
            "registered_target_evidence": True,
            "independent_model_replay_attestation_id": None,
            "independent_model_replay_status": (
                REGISTERED_TARGET_MODEL_INDEPENDENT_REPLAY_STATUS
            ),
            "shared_physical_rows": True,
            "kernel_calls": 0,
            "hidden_law_queries": 0,
            "source_prior_reads": 0,
        }

    @property
    def model_pair_id(self) -> str:
        return self._model_pair_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "closure_bundle": self.closure_bundle.to_document(),
            "row_projections": [
                item.to_document() for item in self.row_projections
            ],
            "relational_context": self.relational_context.to_document(),
            "relational_coordinates": [
                item.to_document()
                for item in self.relational_coordinates
            ],
            "direct_model": self.direct_model.to_document(),
            "quotient_model": self.quotient_model.to_document(),
            "direct_planner_model": (
                self.direct_planner_model.to_document()
            ),
            "quotient_planner_model": (
                self.quotient_planner_model.to_document()
            ),
            "direct_collapse_proof": (
                self.direct_collapse_proof.to_document()
            ),
            "quotient_collapse_proof": (
                self.quotient_collapse_proof.to_document()
            ),
            "threshold_profile": self.threshold_profile.to_document(),
            "model_pair_id": self.model_pair_id,
        }


def build_registered_target_cold_h2_models_v1(
    *,
    anchor: final_authority.V072RemoteMainAnchorV1,
    closure_bundle: closure.V072ColdH2ClosureBundleV1,
    row_projections: tuple[
        row_projection.RegisteredConfidenceIntervalSimplexRowProjectionV1,
        ...,
    ],
    relational_context: RegisteredColdH2PublicRelationalContextV1,
) -> RegisteredColdH2ModelPairV1:
    """Build rank-cap-6 ground and relational models from target evidence."""

    if (
        type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or anchor.target_execution_allowed is not True
        or type(closure_bundle) is not closure.V072ColdH2ClosureBundleV1
        or closure_bundle.cap_evidence.evidence_class
        is not closure.ColdH2CapEvidenceClassV1.CONFIRMATORY_REGISTERED
        or type(row_projections) is not tuple
        or not row_projections
        or any(
            type(item)
            is not (
                row_projection
                .RegisteredConfidenceIntervalSimplexRowProjectionV1
            )
            for item in row_projections
        )
        or type(relational_context)
        is not RegisteredColdH2PublicRelationalContextV1
        or relational_context.context_id != closure_bundle.context_id
    ):
        raise RegisteredTargetColdH2ModelBuildLockedV1(
            "registered cold H2 build requires the exact minted anchor, "
            "confirmatory closure, target projections, and rank-cap-6 "
            "relational context"
        )
    projections = tuple(
        sorted(row_projections, key=lambda item: item.projection_id)
    )
    if len({item.projection_id for item in projections}) != len(
        projections
    ):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "registered projection inventory contains replacement"
        )
    rows_by_id = {
        item.row_evidence_id: item
        for item in closure_bundle.all_rows
    }
    projections_by_row = {
        item.row_evidence_id: item for item in projections
    }
    if set(rows_by_id) != set(projections_by_row):
        raise V072ColdH2ModelBuilderInvariantViolation(
            "registered projection inventory is not one-to-one with closure"
        )
    for row_id, projection in projections_by_row.items():
        row = rows_by_id[row_id]
        if (
            projection.confidence_authority.anchor_id != anchor.anchor_id
            or projection.confidence_authority.final_preregistration_id
            != anchor.claim.final_preregistration_id
            or projection.context_id != row.context_id
            or projection.physical_evidence_id
            != row.physical_evidence_id
            or projection.support_epoch_id != row.support_epoch_id
            or projection.confidence_snapshot_id
            != row.confidence_snapshot_id
            or projection.row_replay_verification_id
            != row.row_replay_verification_id
            or projection.state_semantic_id
            != row.state.semantic_state_id
            or projection.action_semantic_id
            != row.action.semantic_action_id
            or projection.remaining_horizon != row.remaining_horizon
            or projection.discovery_support_descriptor_ids
            != tuple(
                item.descriptor_record_id
                for item in row.discovery_support
            )
            or projection.validation_novel_descriptor_ids
            != tuple(
                item.descriptor_record_id
                for item in row.validation_novel
            )
            or projection.interval_row.reward_upper
            > PRODUCTION_REWARD_CEILING
        ):
            raise V072ColdH2ModelBuilderInvariantViolation(
                "registered projection was transplanted or changes row "
                "semantics"
            )
    source_catalogues = (
        (closure_bundle.root_catalogue,)
        + closure_bundle.child_catalogues
    )
    state_ids = {
        catalogue.state.semantic_state_id: ground_state_id_v1(
            closure_bundle.context_id,
            catalogue.state,
            catalogue.remaining_horizon,
        )
        for catalogue in source_catalogues
    }
    direct_catalogues = tuple(
        sorted(
            (
                robust.StateActionCatalogueV1(
                    state_ids[catalogue.state.semantic_state_id],
                    state_ids[catalogue.state.semantic_state_id],
                    tuple(
                        sorted(
                            (
                                robust.CatalogueActionV1(
                                    ground_action_id_v1(
                                        closure_bundle.context_id,
                                        catalogue.state,
                                        catalogue.remaining_horizon,
                                        action,
                                    ),
                                    ground_action_id_v1(
                                        closure_bundle.context_id,
                                        catalogue.state,
                                        catalogue.remaining_horizon,
                                        action,
                                    ),
                                )
                                for action in catalogue.actions
                            ),
                            key=lambda item: item.action_id,
                        )
                    ),
                )
                for catalogue in source_catalogues
            ),
            key=lambda item: item.state_id,
        )
    )
    destinations_by_id: dict[str, robust.RegisteredDestinationV1] = {}
    for projection in projections:
        for destination in projection.destinations:
            existing = destinations_by_id.setdefault(
                destination.destination_id,
                destination,
            )
            if existing != destination:
                raise V072ColdH2ModelBuilderInvariantViolation(
                    "registered destination ID has conflicting semantics"
                )
    interval_rows = tuple(
        sorted(
            (item.interval_row for item in projections),
            key=lambda item: item.row_id,
        )
    )
    physical_ids = tuple(
        sorted(item.physical_evidence_id for item in projections)
    )
    projection_ids = tuple(
        sorted(item.projection_id for item in projections)
    )
    direct_model = RegisteredColdH2IntervalSimplexModelV1(
        _REGISTERED_MODEL_MINTING_SENTINEL,
        closure_bundle.context_id,
        closure_bundle.closure_id,
        ColdH2ModelKindV1.GROUND_DIRECT,
        state_ids[closure_bundle.root_state.semantic_state_id],
        direct_catalogues,
        tuple(
            sorted(
                destinations_by_id.values(),
                key=lambda item: item.destination_id,
            )
        ),
        interval_rows,
        (),
        physical_ids,
        projection_ids,
        None,
    )
    state_coordinates: dict[str, ObservationRelationalCoordinateV1] = {}
    action_coordinates: dict[
        tuple[str, str], ObservationRelationalCoordinateV1
    ] = {}
    for catalogue in source_catalogues:
        state_id = state_ids[catalogue.state.semantic_state_id]
        state_value, action_values = (
            _registered_replay_catalogue_relational_values(
                relational_context,
                catalogue,
            )
        )
        state_coordinates[state_id] = ObservationRelationalCoordinateV1(
            RelationalCoordinateRoleV1.STATE,
            catalogue.remaining_horizon,
            _base_coordinate_signature(
                program="cardinality_actions(legal_actions)",
                value=state_value,
            ),
        )
        for action in catalogue.actions:
            action_id = ground_action_id_v1(
                closure_bundle.context_id,
                catalogue.state,
                catalogue.remaining_horizon,
                action,
            )
            action_coordinates[(state_id, action_id)] = (
                ObservationRelationalCoordinateV1(
                    RelationalCoordinateRoleV1.ACTION,
                    catalogue.remaining_horizon,
                    _base_coordinate_signature(
                        program=(
                            "cardinality_resources(linked_filter("
                            "action_anchor,active_resources))"
                        ),
                        value=action_values[action.action_record_id],
                    ),
                )
            )
    quotient_catalogues: list[robust.StateActionCatalogueV1] = []
    concretizers: list[
        robust.DistinctActionConcretizerEntryV1
    ] = []
    for direct_catalogue in direct_catalogues:
        actions = tuple(
            robust.CatalogueActionV1(
                action.action_id,
                action_coordinates[
                    (direct_catalogue.state_id, action.action_id)
                ].coordinate_id,
            )
            for action in direct_catalogue.actions
        )
        quotient_catalogue = robust.StateActionCatalogueV1(
            direct_catalogue.state_id,
            state_coordinates[
                direct_catalogue.state_id
            ].coordinate_id,
            actions,
        )
        quotient_catalogues.append(quotient_catalogue)
        groups: dict[str, list[str]] = {}
        for action in actions:
            groups.setdefault(
                action.action_coordinate_key,
                [],
            ).append(action.action_id)
        concretizers.extend(
            robust.DistinctActionConcretizerEntryV1(
                quotient_catalogue.state_coordinate_key,
                quotient_catalogue.state_id,
                coordinate,
                tuple(sorted(action_ids)),
            )
            for coordinate, action_ids in groups.items()
        )
    quotient_model = RegisteredColdH2IntervalSimplexModelV1(
        _REGISTERED_MODEL_MINTING_SENTINEL,
        closure_bundle.context_id,
        closure_bundle.closure_id,
        ColdH2ModelKindV1.OBSERVATION_RELATIONAL_QUOTIENT,
        direct_model.root_state_id,
        tuple(
            sorted(
                quotient_catalogues,
                key=lambda item: item.state_id,
            )
        ),
        direct_model.destinations,
        direct_model.rows,
        tuple(
            sorted(
                concretizers,
                key=lambda item: item.concretizer_entry_id,
            )
        ),
        physical_ids,
        projection_ids,
        relational_context.relational_context_id,
    )
    direct_planner, direct_proof = _registered_planner_projection(
        direct_model
    )
    quotient_planner, quotient_proof = (
        _registered_planner_projection(quotient_model)
    )
    threshold = robust.RobustThresholdProfileV1(
        closure_bundle.context_id,
        PRODUCTION_RISK_TOLERANCE,
        PRODUCTION_REWARD_CEILING,
    )
    coordinates = tuple(
        sorted(
            {
                item.coordinate_id: item
                for item in (
                    *state_coordinates.values(),
                    *action_coordinates.values(),
                )
            }.values(),
            key=lambda item: item.coordinate_id,
        )
    )
    return RegisteredColdH2ModelPairV1(
        _REGISTERED_PAIR_MINTING_SENTINEL,
        anchor.anchor_id,
        anchor.claim.final_preregistration_id,
        closure_bundle,
        projections,
        relational_context,
        coordinates,
        direct_model,
        quotient_model,
        direct_planner,
        quotient_planner,
        direct_proof,
        quotient_proof,
        threshold,
    )


__all__ = [
    "BOUNDED_REFINEMENT_STATUS",
    "COORDINATE_DERIVATION",
    "ColdH2PlannerProjectionV1",
    "ColdH2PublicRelationalContextV1",
    "ColdH2IntervalSimplexModelV1",
    "ColdH2ModelKindV1",
    "DEVELOPMENT_REWARD_CEILING",
    "DEVELOPMENT_RANK_PROFILE",
    "DEVELOPMENT_RISK_TOLERANCE",
    "FORBIDDEN_COORDINATE_KEYS",
    "ObservationRelationalCoordinateV1",
    "PROFILE_KEY",
    "PRODUCTION_RANK_PROFILE",
    "REGISTERED_TARGET_MODEL_BUILD_STATUS",
    "REGISTERED_TARGET_MODEL_INDEPENDENT_REPLAY_STATUS",
    "RegisteredColdH2IntervalSimplexModelV1",
    "RegisteredColdH2ModelPairV1",
    "RegisteredColdH2PublicRelationalContextV1",
    "RegisteredRowBoundOtherCollapseProofV1",
    "RegisteredTargetColdH2ModelBuildLockedV1",
    "RelationalCoordinateRoleV1",
    "RowBoundOtherCollapseEntryV1",
    "RowBoundOtherCollapseProofV1",
    "RowProjectionEvidenceClassV1",
    "SCHEMA_VERSION",
    "V072ColdH2ModelBuilderInvariantViolation",
    "V072ColdH2GroundDirectSnapshotV1",
    "V072ColdH2ModelPairV1",
    "VerifiedColdH2ConfidenceRowProjectionV1",
    "VerifiedConfidenceRowProjectionProtocolV1",
    "bind_verified_confidence_row_projection_v1",
    "build_v072_cold_h2_ground_direct_model_v1",
    "build_registered_target_cold_h2_models_v1",
    "build_v072_cold_h2_models_v1",
    "destination_for_descriptor_v1",
    "development_k4_threshold_profile_v1",
    "registered_cold_h2_relational_context_v1",
    "replay_registered_base_coordinate_values_v1",
    "ground_action_id_v1",
    "ground_state_id_v1",
    "observed_destination_id_v1",
    "other_destination_for_row_v1",
    "row_bound_other_destination_id_v1",
    "replay_v0066_base_coordinate_values_v1",
    "V0066_ACTION_PROGRAM_ID",
    "V0066_SOURCE_SKELETON_ID",
    "V0066_STATE_PROGRAM_ID",
    "V0068_BASE_COORDINATE_PROFILE_ID",
]
