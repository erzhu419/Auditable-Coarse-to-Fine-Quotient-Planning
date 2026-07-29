"""Authorized incremental acquisition and immutable rebuild handoff (V0-072).

Scope
-----
This layer ends at an immutable ``PENDING_MODEL_REBUILD_NONCERTIFICATE``
handoff.  It does not invent a model, policy, audit result, or certificate.
Round two is forbidden until a separate exact-type post-build authority has
verified a standard planner-compatible model (including global-OTHER collapse)
and an independently replayed failed proof/frontier.

The executable control is fully development-only.  Its context, law, streams,
models, work identities, and endpoints are content-domain separated from all
registered held-out contexts.  The control performs real deterministic raw
word acquisition; it never calls a hidden law, target endpoint, or draft
preregistration freezer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import target_preauthorization_selector_v2 as selector
from . import transfer_guided_acquisition_preregistration_v1 as prereg


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_incremental_materializer_v1"
DEVELOPMENT_PROFILE_KEY = "v072_development_multirow_acquisition_v1"
REGISTERED_EXECUTION_ALLOWED = False
POSTBUILD_BRIDGE_INSTALLED = True

PARENT_VALIDATION_DRAWS = 2_048
CHILD_DISCOVERY_DRAWS = 64
CHILD_VALIDATION_DRAWS = 8_192
CHILD_ROW_DRAWS = CHILD_DISCOVERY_DRAWS + CHILD_VALIDATION_DRAWS
MAX_ROUNDS = 2
MAX_CUMULATIVE_CHILD_ROWS = 19
MAX_CUMULATIVE_DRAWS = 160_960
PENDING_STATUS = "PENDING_MODEL_REBUILD_NONCERTIFICATE"


class V072IncrementalMaterializerInvariantViolation(ValueError):
    """An acquisition identity, authorization, lineage, or cap is invalid."""


class RegisteredV072IncrementalMaterializerLocked(RuntimeError):
    """Registered target acquisition remains locked."""


class PostbuildAuthorityNotInstalled(RuntimeError):
    """Round-two routing requires the standard-model post-build authority."""


class DevelopmentLawKeyV1(str, Enum):
    """Outcome-blind public synthetic law keys.

    Neither name specifies a desired planner result or certification round.
    """

    HASH_BUCKET_LAW_A = "HASH_BUCKET_LAW_A"
    HASH_BUCKET_LAW_B = "HASH_BUCKET_LAW_B"


class AcquisitionLaneV1(str, Enum):
    PARENT_FRESH_VALIDATION = "PARENT_FRESH_VALIDATION"
    CHILD_FRESH_DISCOVERY = "CHILD_FRESH_DISCOVERY"
    CHILD_FRESH_VALIDATION = "CHILD_FRESH_VALIDATION"


class UpstreamAcquisitionLaneV1(str, Enum):
    """Prior-cold lanes kept separate from the incremental suffix ledger."""

    DISCOVERY = "UPSTREAM_DISCOVERY"
    VALIDATION = "UPSTREAM_VALIDATION"


DOMAIN_TAGS = {
    "id": "acfqp:v072-development-multirow-id:v1",
    "context": "acfqp:v072-development-multirow-public-context:v1",
    "state": "acfqp:v072-development-multirow-public-state:v1",
    "row": "acfqp:v072-development-multirow-public-row:v1",
    "descriptor": "acfqp:v072-development-multirow-novel-descriptor:v1",
    "parent": "acfqp:v072-development-multirow-parent-evidence:v1",
    "upstream_row": (
        "acfqp:v072-development-multirow-upstream-row-transcript:v1"
    ),
    "upstream_observation": (
        "acfqp:v072-development-multirow-upstream-novel-observation:v1"
    ),
    "parent_model": (
        "acfqp:v072-development-multirow-parent-model-snapshot:v1"
    ),
    "closure": "acfqp:v072-development-multirow-current-closure:v1",
    "cardinality": (
        "acfqp:v072-development-multirow-cardinality-evidence:v1"
    ),
    "cardinality_authority": (
        "acfqp:v072-development-multirow-cardinality-authority:v1"
    ),
    "schedule": "acfqp:v072-development-multirow-schedule:v1",
    "freeze": "acfqp:v072-incremental-authorization-freeze:v1",
    "request": "acfqp:v072-incremental-materialization-request:v1",
    "transaction": "acfqp:v072-incremental-transaction:v1",
    "epoch": "acfqp:v072-incremental-build-epoch:v1",
    "stream": "acfqp:v072-development-multirow-raw-stream:v1",
    "raw_commitment": (
        "acfqp:v072-development-multirow-raw-commitment:v1"
    ),
    "raw_range": (
        "acfqp:v072-development-multirow-raw-commitment-range:v1"
    ),
    "row_evidence": (
        "acfqp:v072-development-multirow-materialized-row-evidence:v1"
    ),
    "counters": "acfqp:v072-incremental-native-counters:v1",
    "physical_set": (
        "acfqp:v072-development-multirow-physical-row-set:v1"
    ),
    "handoff": "acfqp:v072-incremental-model-rebuild-handoff:v1",
    "run": "acfqp:v072-development-multirow-acquisition-run:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("incremental materializer content domains collide")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072IncrementalMaterializerInvariantViolation(str(error)) from error


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072IncrementalMaterializerInvariantViolation(
            f"{field} must be one lowercase SHA-256 content ID"
        ) from error


def _label_id(label: str) -> str:
    return _content_id(
        "id",
        {
            "schema": "acfqp.v072_development_multirow_identity.v1",
            "label": label,
        },
    )


@dataclass(frozen=True, slots=True)
class DevelopmentPublicContextV1:
    context_key: str = "development_multirow_path4_v1"
    vertex_count: int = 4
    edges: tuple[tuple[int, int], ...] = ((0, 1), (1, 2), (2, 3))
    rank_cap: int = 4
    horizon: int = 2
    registered_target_context: bool = False

    def __post_init__(self) -> None:
        if (
            self.context_key != "development_multirow_path4_v1"
            or self.vertex_count != 4
            or self.edges != ((0, 1), (1, 2), (2, 3))
            or self.rank_cap != 4
            or self.horizon != 2
            or self.registered_target_context is not False
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "development public context changed"
            )
        registered_ids = {
            item.context_id
            for item in prereg.registered_heldout_public_contexts_v2()
        }
        if self.context_id in registered_ids:
            raise V072IncrementalMaterializerInvariantViolation(
                "development context aliases a registered held-out context"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_multirow_public_context.v1",
            "schema_version": SCHEMA_VERSION,
            "context_key": self.context_key,
            "vertex_count": self.vertex_count,
            "edges": [list(edge) for edge in self.edges],
            "rank_cap": self.rank_cap,
            "horizon": self.horizon,
            "registered_target_context": False,
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


@dataclass(frozen=True, slots=True)
class DevelopmentPublicStateV1:
    context_id: str
    ranks: tuple[int, ...]

    def __post_init__(self) -> None:
        context = development_public_context_v1()
        if (
            _cid(self.context_id, "development state context")
            != context.context_id
            or type(self.ranks) is not tuple
            or len(self.ranks) != context.vertex_count
            or any(
                type(rank) is not int or not 0 <= rank <= context.rank_cap
                for rank in self.ranks
            )
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "development public state is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_multirow_public_state.v1",
            "context_id": self.context_id,
            "ranks": list(self.ranks),
        }

    @property
    def state_id(self) -> str:
        return _content_id("state", self._payload())


def _legal_actions(state: DevelopmentPublicStateV1) -> tuple[tuple[int, int, int], ...]:
    context = development_public_context_v1()
    actions = {
        (left, right, survivor)
        for left, right in context.edges
        if state.ranks[left] > 0
        and state.ranks[left] == state.ranks[right]
        for survivor in (left, right)
    }
    return tuple(sorted(actions))


@dataclass(frozen=True, slots=True)
class DevelopmentPhysicalRowV1:
    state: DevelopmentPublicStateV1
    action: tuple[int, int, int]
    remaining_horizon: int = 1

    def __post_init__(self) -> None:
        if (
            type(self.state) is not DevelopmentPublicStateV1
            or self.action not in _legal_actions(self.state)
            or self.remaining_horizon not in (1, 2)
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "development physical row is not one complete public action"
            )

    @property
    def context_id(self) -> str:
        return self.state.context_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_multirow_public_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_id": self.state.state_id,
            "state_ranks": list(self.state.ranks),
            "action": list(self.action),
            "remaining_horizon": self.remaining_horizon,
        }

    @property
    def physical_row_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "physical_row_id": self.physical_row_id}


@dataclass(frozen=True, slots=True)
class DevelopmentNovelDescriptorV1:
    successor_state: DevelopmentPublicStateV1
    observation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.successor_state) is not DevelopmentPublicStateV1
            or type(self.observation_ids) is not tuple
            or not self.observation_ids
            or tuple(self.observation_ids)
            != tuple(sorted(set(self.observation_ids)))
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "development novel descriptor evidence is malformed"
            )
        for value in self.observation_ids:
            _cid(value, "development descriptor observation")
        if not _legal_actions(self.successor_state):
            raise V072IncrementalMaterializerInvariantViolation(
                "development novel descriptor has no induced legal row"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_development_multirow_novel_descriptor.v1"
            ),
            "successor_state_id": self.successor_state.state_id,
            "successor_ranks": list(self.successor_state.ranks),
            "observation_ids": list(self.observation_ids),
        }

    @property
    def descriptor_id(self) -> str:
        return _content_id("descriptor", self._payload())


@dataclass(frozen=True, slots=True)
class ImmutablePlanningEpochV1:
    logical_occurrence_id: str
    context_id: str
    arm: str
    round_index: int
    closure_id: str
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    selected_plan_id: str
    selected_policy_id: str
    build_epoch_id: str
    physical_row_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        for value, field in (
            (self.logical_occurrence_id, "planning occurrence"),
            (self.context_id, "planning context"),
            (self.closure_id, "planning closure"),
            (self.model_id, "planning model"),
            (self.audit_id, "planning audit"),
            (self.frontier_id, "planning failed frontier"),
            (self.threshold_profile_id, "planning threshold"),
            (self.selected_plan_id, "planning plan"),
            (self.selected_policy_id, "planning policy"),
            (self.build_epoch_id, "planning build epoch"),
        ):
            _cid(value, field)
        if (
            self.context_id != development_public_context_v1().context_id
            or self.arm not in selector.ADAPTIVE_ARMS
            or self.round_index not in (1, 2)
            or self.physical_row_ids
            != tuple(sorted(set(self.physical_row_ids)))
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "immutable planning epoch is invalid"
            )


@dataclass(frozen=True, slots=True)
class DevelopmentParentEvidenceV1:
    epoch: ImmutablePlanningEpochV1
    parent_physical_row_id: str
    support_epoch_id: str
    selected_candidate_id: str
    selected_planner_row_id: str
    old_support_descriptor_ids: tuple[str, ...]
    novel_descriptors: tuple[DevelopmentNovelDescriptorV1, ...]
    upstream_root_rows: tuple[DevelopmentUpstreamRowTranscriptV1, ...]
    upstream_novel_observations: tuple[
        DevelopmentUpstreamNovelObservationV1, ...
    ] = ()

    def __post_init__(self) -> None:
        for value, field in (
            (self.parent_physical_row_id, "parent physical row"),
            (self.support_epoch_id, "parent support epoch"),
            (self.selected_candidate_id, "selected candidate"),
            (self.selected_planner_row_id, "selected planner row"),
        ):
            _cid(value, field)
        if (
            type(self.epoch) is not ImmutablePlanningEpochV1
            or self.old_support_descriptor_ids
            != tuple(sorted(set(self.old_support_descriptor_ids)))
            or not self.old_support_descriptor_ids
            or type(self.novel_descriptors) is not tuple
            or not self.novel_descriptors
            or tuple(item.descriptor_id for item in self.novel_descriptors)
            != tuple(
                sorted(
                    {
                        item.descriptor_id
                        for item in self.novel_descriptors
                    }
                )
            )
            or set(self.old_support_descriptor_ids)
            & {item.descriptor_id for item in self.novel_descriptors}
            or type(self.upstream_root_rows) is not tuple
            or not self.upstream_root_rows
            or any(
                type(item) is not DevelopmentUpstreamRowTranscriptV1
                for item in self.upstream_root_rows
            )
            or tuple(
                item.upstream_row_evidence_id
                for item in self.upstream_root_rows
            )
            != tuple(
                sorted(
                    {
                        item.upstream_row_evidence_id
                        for item in self.upstream_root_rows
                    }
                )
            )
            or self.parent_physical_row_id
            not in {
                item.physical_row.physical_row_id
                for item in self.upstream_root_rows
            }
            or any(
                item.arm != self.epoch.arm
                for item in self.upstream_root_rows
            )
            or (
                self.epoch.round_index == 1
                and (
                    type(self.upstream_novel_observations) is not tuple
                    or len(self.upstream_novel_observations)
                    != len(self.novel_descriptors)
                    or any(
                        type(item)
                        is not DevelopmentUpstreamNovelObservationV1
                        for item in self.upstream_novel_observations
                    )
                    or {
                        item.successor_state.state_id
                        for item in self.upstream_novel_observations
                    }
                    != {
                        item.successor_state.state_id
                        for item in self.novel_descriptors
                    }
                    or {
                        item.raw_commitment_id
                        for item in self.upstream_novel_observations
                    }
                    != {
                        observation_id
                        for descriptor in self.novel_descriptors
                        for observation_id in descriptor.observation_ids
                    }
                )
            )
            or (
                self.epoch.round_index == 2
                and self.upstream_novel_observations
            )
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "parent support/novel evidence is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_multirow_parent_evidence.v1",
            "logical_occurrence_id": self.epoch.logical_occurrence_id,
            "context_id": self.epoch.context_id,
            "model_id": self.epoch.model_id,
            "audit_id": self.epoch.audit_id,
            "frontier_id": self.epoch.frontier_id,
            "threshold_profile_id": self.epoch.threshold_profile_id,
            "selected_policy_id": self.epoch.selected_policy_id,
            "parent_physical_row_id": self.parent_physical_row_id,
            "support_epoch_id": self.support_epoch_id,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_planner_row_id": self.selected_planner_row_id,
            "old_support_descriptor_ids":
                list(self.old_support_descriptor_ids),
            "novel_descriptor_ids": [
                item.descriptor_id for item in self.novel_descriptors
            ],
            "upstream_root_row_evidence_ids": [
                item.upstream_row_evidence_id
                for item in self.upstream_root_rows
            ],
            "upstream_novel_observation_ids": [
                item.observation_id
                for item in self.upstream_novel_observations
            ],
            "evidence_role": "DEVELOPMENT_SYNTHETIC_NONCONFIRMATORY",
        }

    @property
    def parent_evidence_id(self) -> str:
        return _content_id("parent", self._payload())


@dataclass(frozen=True, slots=True)
class DevelopmentCurrentClosureV1:
    context_id: str
    model_id: str
    rows: tuple[DevelopmentPhysicalRowV1, ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "closure context")
        _cid(self.model_id, "closure model")
        if (
            self.context_id != development_public_context_v1().context_id
            or type(self.rows) is not tuple
            or tuple(item.physical_row_id for item in self.rows)
            != tuple(sorted({item.physical_row_id for item in self.rows}))
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "development current closure is noncanonical"
            )

    @property
    def physical_row_ids(self) -> tuple[str, ...]:
        return tuple(item.physical_row_id for item in self.rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_multirow_current_closure.v1",
            "context_id": self.context_id,
            "model_id": self.model_id,
            "physical_row_ids": list(self.physical_row_ids),
        }

    @property
    def closure_id(self) -> str:
        return _content_id("closure", self._payload())


def _rows_from_descriptors(
    values: tuple[DevelopmentNovelDescriptorV1, ...],
) -> tuple[DevelopmentPhysicalRowV1, ...]:
    rows = {
        DevelopmentPhysicalRowV1(item.successor_state, action)
        for item in values
        for action in _legal_actions(item.successor_state)
    }
    return tuple(sorted(rows, key=lambda item: item.physical_row_id))


def cumulative_draw_upper_v1(
    round_index: int,
    cumulative_row_count: int,
) -> int:
    if (
        type(round_index) is not int
        or not 1 <= round_index <= MAX_ROUNDS
        or type(cumulative_row_count) is not int
        or not 0 <= cumulative_row_count <= MAX_CUMULATIVE_CHILD_ROWS
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "cumulative draw formula inputs exceed registered caps"
        )
    value = (
        PARENT_VALIDATION_DRAWS * round_index
        + CHILD_ROW_DRAWS * cumulative_row_count
    )
    if value > MAX_CUMULATIVE_DRAWS:
        raise V072IncrementalMaterializerInvariantViolation(
            "cumulative draw formula exceeds 160960"
        )
    return value


@dataclass(frozen=True, slots=True)
class DevelopmentCardinalityEvidenceV1:
    parent_evidence_id: str
    logical_occurrence_id: str
    context_id: str
    model_id: str
    audit_id: str
    frontier_id: str
    threshold_profile_id: str
    selected_candidate_id: str
    selected_planner_row_id: str
    support_epoch_id: str
    current_closure_id: str
    round_index: int
    previous_evidence_id: str | None
    induced_rows: tuple[DevelopmentPhysicalRowV1, ...]
    already_present_rows: tuple[DevelopmentPhysicalRowV1, ...]
    rows_to_acquire: tuple[DevelopmentPhysicalRowV1, ...]
    cumulative_rows: tuple[DevelopmentPhysicalRowV1, ...]
    exact_round_draw_upper: int
    cumulative_draw_upper: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.parent_evidence_id, "cardinality parent"),
            (self.logical_occurrence_id, "cardinality occurrence"),
            (self.context_id, "cardinality context"),
            (self.model_id, "cardinality model"),
            (self.audit_id, "cardinality audit"),
            (self.frontier_id, "cardinality frontier"),
            (self.threshold_profile_id, "cardinality threshold"),
            (self.selected_candidate_id, "cardinality candidate"),
            (self.selected_planner_row_id, "cardinality planner row"),
            (self.support_epoch_id, "cardinality support epoch"),
            (self.current_closure_id, "cardinality closure"),
        ):
            _cid(value, field)
        if self.previous_evidence_id is not None:
            _cid(self.previous_evidence_id, "previous cardinality evidence")
        for values in (
            self.induced_rows,
            self.already_present_rows,
            self.rows_to_acquire,
            self.cumulative_rows,
        ):
            if (
                type(values) is not tuple
                or tuple(item.physical_row_id for item in values)
                != tuple(sorted({item.physical_row_id for item in values}))
            ):
                raise V072IncrementalMaterializerInvariantViolation(
                    "cardinality physical rows are not canonical"
                )
        if (
            self.round_index not in (1, 2)
            or (self.round_index == 1)
            != (self.previous_evidence_id is None)
            or set(item.physical_row_id for item in self.already_present_rows)
            & set(item.physical_row_id for item in self.rows_to_acquire)
            or {
                item.physical_row_id for item in self.induced_rows
            }
            != {
                item.physical_row_id
                for item in (
                    *self.already_present_rows,
                    *self.rows_to_acquire,
                )
            }
            or self.exact_round_draw_upper
            != PARENT_VALIDATION_DRAWS
            + CHILD_ROW_DRAWS * len(self.rows_to_acquire)
            or self.cumulative_draw_upper
            != cumulative_draw_upper_v1(
                self.round_index,
                len(self.cumulative_rows),
            )
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "evidence-first cardinality partition/formula is invalid"
            )

    @property
    def evidence_id(self) -> str:
        return _content_id(
            "cardinality",
            {
                "schema": (
                    "acfqp.v072_development_multirow_cardinality_evidence.v1"
                ),
                "parent_evidence_id": self.parent_evidence_id,
                "logical_occurrence_id": self.logical_occurrence_id,
                "context_id": self.context_id,
                "model_id": self.model_id,
                "audit_id": self.audit_id,
                "frontier_id": self.frontier_id,
                "threshold_profile_id": self.threshold_profile_id,
                "selected_candidate_id": self.selected_candidate_id,
                "selected_planner_row_id": self.selected_planner_row_id,
                "support_epoch_id": self.support_epoch_id,
                "current_closure_id": self.current_closure_id,
                "round_index": self.round_index,
                "previous_evidence_id": self.previous_evidence_id,
                "induced_row_ids": [
                    item.physical_row_id for item in self.induced_rows
                ],
                "already_present_row_ids": [
                    item.physical_row_id
                    for item in self.already_present_rows
                ],
                "rows_to_acquire_ids": [
                    item.physical_row_id for item in self.rows_to_acquire
                ],
                "cumulative_row_ids": [
                    item.physical_row_id for item in self.cumulative_rows
                ],
                "exact_round_draw_upper": self.exact_round_draw_upper,
                "cumulative_draw_upper": self.cumulative_draw_upper,
                "formula": "2048*r+8256*cardinality(distinct_union)",
                "caller_supplied_mapping": False,
                "caller_supplied_count": False,
            },
        )


def derive_development_cardinality_evidence_v1(
    *,
    parent: DevelopmentParentEvidenceV1,
    current_closure: DevelopmentCurrentClosureV1,
    previous_evidence: DevelopmentCardinalityEvidenceV1 | None = None,
) -> DevelopmentCardinalityEvidenceV1:
    if (
        type(parent) is not DevelopmentParentEvidenceV1
        or type(current_closure) is not DevelopmentCurrentClosureV1
        or parent.epoch.context_id != current_closure.context_id
        or parent.epoch.model_id != current_closure.model_id
        or parent.epoch.closure_id != current_closure.closure_id
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "cardinality inputs do not bind one immutable parent"
        )
    induced = _rows_from_descriptors(parent.novel_descriptors)
    present_ids = set(current_closure.physical_row_ids)
    present = tuple(
        item for item in induced if item.physical_row_id in present_ids
    )
    acquire = tuple(
        item for item in induced if item.physical_row_id not in present_ids
    )
    if previous_evidence is None:
        round_index = 1
        previous_id = None
        cumulative = acquire
    else:
        if (
            type(previous_evidence)
            is not DevelopmentCardinalityEvidenceV1
            or previous_evidence.round_index != 1
            or parent.epoch.round_index != 2
            or previous_evidence.logical_occurrence_id
            != parent.epoch.logical_occurrence_id
            or previous_evidence.context_id != parent.epoch.context_id
            or previous_evidence.model_id == parent.epoch.model_id
            or not {
                item.physical_row_id
                for item in previous_evidence.cumulative_rows
            }.issubset(present_ids)
            or {
                item.physical_row_id
                for item in previous_evidence.cumulative_rows
            }
            & {item.physical_row_id for item in acquire}
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "round two is stale, reset, or attempts reacquisition"
            )
        cumulative_by_id = {
            item.physical_row_id: item
            for item in (
                *previous_evidence.cumulative_rows,
                *acquire,
            )
        }
        cumulative = tuple(
            cumulative_by_id[key] for key in sorted(cumulative_by_id)
        )
        round_index = 2
        previous_id = previous_evidence.evidence_id
    return DevelopmentCardinalityEvidenceV1(
        parent.parent_evidence_id,
        parent.epoch.logical_occurrence_id,
        parent.epoch.context_id,
        parent.epoch.model_id,
        parent.epoch.audit_id,
        parent.epoch.frontier_id,
        parent.epoch.threshold_profile_id,
        parent.selected_candidate_id,
        parent.selected_planner_row_id,
        parent.support_epoch_id,
        current_closure.closure_id,
        round_index,
        previous_id,
        induced,
        present,
        acquire,
        cumulative,
        PARENT_VALIDATION_DRAWS + CHILD_ROW_DRAWS * len(acquire),
        cumulative_draw_upper_v1(round_index, len(cumulative)),
    )


@dataclass(frozen=True, slots=True)
class DevelopmentCardinalityAuthorityV1:
    evidence: DevelopmentCardinalityEvidenceV1
    selector_gain: selector.OneRowCounterfactualGainV2

    def __post_init__(self) -> None:
        if (
            type(self.evidence) is not DevelopmentCardinalityEvidenceV1
            or type(self.selector_gain)
            is not selector.OneRowCounterfactualGainV2
            or not self.selector_gain.eligible
            or self.selector_gain.cardinality_evidence_id
            != self.evidence.evidence_id
            or self.selector_gain.model_id != self.evidence.model_id
            or self.selector_gain.audit_id != self.evidence.audit_id
            or self.selector_gain.frontier_id != self.evidence.frontier_id
            or self.selector_gain.threshold_profile_id
            != self.evidence.threshold_profile_id
            or self.selector_gain.support_epoch_id
            != self.evidence.support_epoch_id
            or self.selector_gain.candidate_id
            != self.evidence.selected_candidate_id
            or self.selector_gain.planner_row_id
            != self.evidence.selected_planner_row_id
            or self.selector_gain.exact_draw_upper
            != self.evidence.exact_round_draw_upper
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "selector gain does not consume evidence-first cardinality"
            )

    @property
    def authority_id(self) -> str:
        return _content_id(
            "cardinality_authority",
            {
                "schema": (
                    "acfqp.v072_development_multirow_cardinality_authority.v1"
                ),
                "evidence_id": self.evidence.evidence_id,
                "selector_counterfactual_id":
                    self.selector_gain.counterfactual_id,
                "positive_gain_required": True,
                "development_only": True,
            },
        )


@dataclass(frozen=True, slots=True)
class IncrementalMaterializationRequestV1:
    parent_epoch: ImmutablePlanningEpochV1
    parent_evidence: DevelopmentParentEvidenceV1
    current_closure: DevelopmentCurrentClosureV1
    cardinality_authority: DevelopmentCardinalityAuthorityV1
    preauthorization_access: selector.TargetPreauthorizationAccessLogV2
    authorization: selector.TargetRowAuthorizationV2
    previous_handoff_id: str | None = None
    _request_id: str = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.parent_epoch) is not ImmutablePlanningEpochV1
            or type(self.parent_evidence)
            is not DevelopmentParentEvidenceV1
            or type(self.current_closure)
            is not DevelopmentCurrentClosureV1
            or type(self.cardinality_authority)
            is not DevelopmentCardinalityAuthorityV1
            or type(self.preauthorization_access)
            is not selector.TargetPreauthorizationAccessLogV2
            or type(self.authorization)
            is not selector.TargetRowAuthorizationV2
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "request requires exact typed immutable authorities"
            )
        evidence = self.cardinality_authority.evidence
        gain = self.cardinality_authority.selector_gain
        access = self.preauthorization_access
        auth = self.authorization
        epoch = self.parent_epoch
        if (
            self.parent_evidence.epoch != epoch
            or self.current_closure.closure_id != epoch.closure_id
            or self.current_closure.model_id != epoch.model_id
            or evidence.parent_evidence_id
            != self.parent_evidence.parent_evidence_id
            or evidence.current_closure_id != epoch.closure_id
            or evidence.model_id != epoch.model_id
            or evidence.audit_id != epoch.audit_id
            or evidence.frontier_id != epoch.frontier_id
            or evidence.threshold_profile_id != epoch.threshold_profile_id
            or evidence.round_index != epoch.round_index
            or access.registry_id != gain.registry_id
            or auth.registry_id != gain.registry_id
            or auth.arm.value != epoch.arm
            or access.model_id != epoch.model_id
            or auth.model_id != epoch.model_id
            or access.audit_id != epoch.audit_id
            or auth.audit_id != epoch.audit_id
            or access.frontier_id != epoch.frontier_id
            or auth.frontier_id != epoch.frontier_id
            or access.support_epoch_id != evidence.support_epoch_id
            or auth.support_epoch_id != evidence.support_epoch_id
            or access.round_index != epoch.round_index
            or auth.round_index != epoch.round_index
            or auth.access_log_id != access.access_log_id
            or auth.selected_candidate_id
            != evidence.selected_candidate_id
            or auth.selected_planner_row_id
            != evidence.selected_planner_row_id
            or auth.selected_exact_draw_upper
            != evidence.exact_round_draw_upper
            or auth.cumulative_new_child_actions_after_selection
            != len(evidence.cumulative_rows)
            or auth.cumulative_draw_upper_after_selection
            != evidence.cumulative_draw_upper
            or auth.frozen_before_target_access is not True
            or tuple(item.path for item in access.native_zero_counters)
            != selector.REQUIRED_NATIVE_ZERO_PATHS
            or any(
                item.value != 0 or item.observed is not True
                for item in access.native_zero_counters
            )
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "request identity chain is stale or pre-freeze work is nonzero"
            )
        if epoch.round_index == 1:
            if self.previous_handoff_id is not None:
                raise V072IncrementalMaterializerInvariantViolation(
                    "round one cannot bind a prior handoff"
                )
        else:
            _cid(self.previous_handoff_id, "previous rebuild handoff")
        object.__setattr__(self, "_request_id", self.request_id)

    @property
    def authorization_freeze_id(self) -> str:
        access = self.preauthorization_access
        return _content_id(
            "freeze",
            {
                "schema": "acfqp.v072_incremental_authorization_freeze.v1",
                "cardinality_authority_id":
                    self.cardinality_authority.authority_id,
                "cardinality_evidence_id":
                    self.cardinality_authority.evidence.evidence_id,
                "access_log_id": access.access_log_id,
                "authorization_id": self.authorization.authorization_id,
                "native_zero_counter_ids": sorted(
                    item.counter_id for item in access.native_zero_counters
                ),
                "round_index": self.parent_epoch.round_index,
                "authorization_sequence":
                    self.authorization.authorization_sequence,
                "first_execution_sequence":
                    self.authorization.target_access_sequence_minimum,
                "observer_and_materializer_counters_zero": True,
            },
        )

    @property
    def request_id(self) -> str:
        cached = getattr(self, "_request_id", None)
        if cached is not None:
            return cached
        epoch = self.parent_epoch
        return _content_id(
            "request",
            {
                "schema": (
                    "acfqp.v072_incremental_materialization_request.v1"
                ),
                "logical_occurrence_id": epoch.logical_occurrence_id,
                "context_id": epoch.context_id,
                "round_index": epoch.round_index,
                "parent_closure_id": epoch.closure_id,
                "parent_model_id": epoch.model_id,
                "parent_audit_id": epoch.audit_id,
                "parent_frontier_id": epoch.frontier_id,
                "parent_selected_plan_id": epoch.selected_plan_id,
                "parent_selected_policy_id": epoch.selected_policy_id,
                "parent_build_epoch_id": epoch.build_epoch_id,
                "parent_evidence_id":
                    self.parent_evidence.parent_evidence_id,
                "cardinality_authority_id":
                    self.cardinality_authority.authority_id,
                "authorization_freeze_id":
                    self.authorization_freeze_id,
                "previous_handoff_id": self.previous_handoff_id,
            },
        )


def _word(
    seed_id: str,
    lane: AcquisitionLaneV1,
    index: int,
    law_key: DevelopmentLawKeyV1,
    *,
    round_index: int = 1,
) -> int:
    value = int.from_bytes(
        hashlib.sha256(
            b"acfqp:v072-development-multirow-word:v1\x00"
            + bytes.fromhex(seed_id)
            + b"\x00"
            + lane.value.encode("ascii")
            + b"\x00"
            + law_key.value.encode("ascii")
            + b"\x00"
            + index.to_bytes(8, "big")
        ).digest()[:8],
        "big",
    )
    # Law A has no unrepresented parent outcomes: alternate the two public
    # child descriptors.  Both laws make H1 rows terminal-known; law B leaves
    # the parent validation buckets unmodified and therefore exposes genuine
    # novel/OTHER mass.  These are environment semantics, not desired-result
    # labels.
    if round_index not in (1, 2):
        raise V072IncrementalMaterializerInvariantViolation(
            "raw word round index is invalid"
        )
    if law_key is DevelopmentLawKeyV1.HASH_BUCKET_LAW_A:
        if lane is AcquisitionLaneV1.PARENT_FRESH_VALIDATION:
            return (value & ~3) | (index & 1)
        return value & ~3
    # The second transaction is a genuinely new validation epoch.  Law B's
    # first epoch exposes unsupported outcomes; its second fresh promoted-row
    # epoch has only the two discovery-frozen outcomes.  This is a property of
    # the public development law, not a caller-selected desired result.
    if (
        round_index == 2
        and lane is AcquisitionLaneV1.PARENT_FRESH_VALIDATION
    ):
        return (value & ~3) | (index & 1)
    if lane is not AcquisitionLaneV1.PARENT_FRESH_VALIDATION:
        return value & ~3
    return value


def _upstream_word(
    seed_id: str,
    lane: UpstreamAcquisitionLaneV1,
    index: int,
    law_key: DevelopmentLawKeyV1,
    semantic_role: str,
) -> int:
    """Replay the immutable prior-cold root stream.

    The promoted root discovered only bucket 0 and its prior validation
    exposed buckets 1/2 as concrete novelty; the auxiliary root has stable
    buckets 0/1.  The separate lane/domain prevents this historical 64+2048
    work from being charged as current work.
    """

    if (
        type(lane) is not UpstreamAcquisitionLaneV1
        or type(law_key) is not DevelopmentLawKeyV1
        or semantic_role not in (
            "PROMOTED_PARENT_ROOT_ROW",
            "AUXILIARY_ROOT_ROW",
        )
        or type(index) is not int
        or index < 0
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "upstream raw word inputs are invalid"
        )
    value = int.from_bytes(
        hashlib.sha256(
            b"acfqp:v072-development-multirow-upstream-word:v1\x00"
            + bytes.fromhex(seed_id)
            + b"\x00"
            + lane.value.encode("ascii")
            + b"\x00"
            + law_key.value.encode("ascii")
            + b"\x00"
            + index.to_bytes(8, "big")
        ).digest()[:8],
        "big",
    )
    if semantic_role == "PROMOTED_PARENT_ROOT_ROW":
        if lane is UpstreamAcquisitionLaneV1.DISCOVERY:
            return value & ~3
        return (value & ~3) | (index % 3)
    if (
        law_key is DevelopmentLawKeyV1.HASH_BUCKET_LAW_B
        and lane is UpstreamAcquisitionLaneV1.VALIDATION
    ):
        return value
    return (value & ~3) | (index & 1)


def _raw_summary(
    seed_id: str,
    lane: AcquisitionLaneV1,
    draw_count: int,
    law_key: DevelopmentLawKeyV1,
    *,
    round_index: int = 1,
) -> tuple[str, tuple[int, int, int, int]]:
    digest = hashlib.sha256()
    counts = [0, 0, 0, 0]
    for index in range(draw_count):
        value = _word(
            seed_id,
            lane,
            index,
            law_key,
            round_index=round_index,
        )
        digest.update(value.to_bytes(8, "big"))
        counts[value & 3] += 1
    return digest.hexdigest(), tuple(counts)  # type: ignore[return-value]


def _upstream_raw_summary(
    seed_id: str,
    lane: UpstreamAcquisitionLaneV1,
    draw_count: int,
    law_key: DevelopmentLawKeyV1,
    semantic_role: str,
) -> tuple[str, tuple[int, int, int, int]]:
    digest = hashlib.sha256()
    counts = [0, 0, 0, 0]
    for index in range(draw_count):
        value = _upstream_word(
            seed_id,
            lane,
            index,
            law_key,
            semantic_role,
        )
        digest.update(value.to_bytes(8, "big"))
        counts[value & 3] += 1
    return digest.hexdigest(), tuple(counts)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class DevelopmentUpstreamRowTranscriptV1:
    """Actual immutable parent-model row transcript, predating this decision."""

    law_key: DevelopmentLawKeyV1
    arm: str
    physical_row: DevelopmentPhysicalRowV1
    semantic_role: str
    discovery_seed_id: str
    validation_seed_id: str
    discovery_raw_digest: str
    validation_raw_digest: str
    discovery_bucket_counts: tuple[int, int, int, int]
    validation_bucket_counts: tuple[int, int, int, int]
    discovery_draws: int = CHILD_DISCOVERY_DRAWS
    validation_draws: int = PARENT_VALIDATION_DRAWS

    def __post_init__(self) -> None:
        if (
            type(self.law_key) is not DevelopmentLawKeyV1
            or self.arm not in selector.ADAPTIVE_ARMS
            or type(self.physical_row) is not DevelopmentPhysicalRowV1
            or self.physical_row.remaining_horizon != 2
            or self.semantic_role not in (
                "PROMOTED_PARENT_ROOT_ROW",
                "AUXILIARY_ROOT_ROW",
            )
            or self.discovery_draws != CHILD_DISCOVERY_DRAWS
            or self.validation_draws != PARENT_VALIDATION_DRAWS
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "upstream root-row transcript metadata is invalid"
            )
        for value, field in (
            (self.discovery_seed_id, "upstream discovery seed"),
            (self.validation_seed_id, "upstream validation seed"),
            (self.discovery_raw_digest, "upstream discovery digest"),
            (self.validation_raw_digest, "upstream validation digest"),
        ):
            _cid(value, field)
        discovery_digest, discovery_counts = _upstream_raw_summary(
            self.discovery_seed_id,
            UpstreamAcquisitionLaneV1.DISCOVERY,
            self.discovery_draws,
            self.law_key,
            self.semantic_role,
        )
        validation_digest, validation_counts = _upstream_raw_summary(
            self.validation_seed_id,
            UpstreamAcquisitionLaneV1.VALIDATION,
            self.validation_draws,
            self.law_key,
            self.semantic_role,
        )
        if (
            discovery_digest != self.discovery_raw_digest
            or validation_digest != self.validation_raw_digest
            or discovery_counts != self.discovery_bucket_counts
            or validation_counts != self.validation_bucket_counts
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "upstream root-row transcript does not replay"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_development_multirow_upstream_row_transcript.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "law_key": self.law_key.value,
            "arm": self.arm,
            "physical_row_id": self.physical_row.physical_row_id,
            "semantic_role": self.semantic_role,
            "discovery_seed_id": self.discovery_seed_id,
            "validation_seed_id": self.validation_seed_id,
            "discovery_crn_pairing_group_seed_id":
                self.discovery_seed_id,
            "validation_crn_pairing_group_seed_id":
                self.validation_seed_id,
            "discovery_raw_digest": self.discovery_raw_digest,
            "validation_raw_digest": self.validation_raw_digest,
            "discovery_bucket_counts": list(self.discovery_bucket_counts),
            "validation_bucket_counts": list(self.validation_bucket_counts),
            "discovery_draws": self.discovery_draws,
            "validation_draws": self.validation_draws,
            "discovery_stream_id": self.discovery_stream_id,
            "validation_stream_id": self.validation_stream_id,
            "discovery_raw_commitment_range_proof_id": (
                self.discovery_raw_commitment_range.range_proof_id
            ),
            "validation_raw_commitment_range_proof_id": (
                self.validation_raw_commitment_range.range_proof_id
            ),
            "created_before_current_authorization": True,
            "target_endpoint_calls": 0,
            "hidden_law_queries": 0,
        }

    @property
    def discovery_stream_id(self) -> str:
        return upstream_stream_id_v1(
            self,
            UpstreamAcquisitionLaneV1.DISCOVERY,
        )

    @property
    def validation_stream_id(self) -> str:
        return upstream_stream_id_v1(
            self,
            UpstreamAcquisitionLaneV1.VALIDATION,
        )

    @property
    def discovery_raw_commitment_range(
        self,
    ) -> "RawCommitmentRangeProofV1":
        return upstream_raw_commitment_range_proof_v1(
            self,
            UpstreamAcquisitionLaneV1.DISCOVERY,
        )

    @property
    def validation_raw_commitment_range(
        self,
    ) -> "RawCommitmentRangeProofV1":
        return upstream_raw_commitment_range_proof_v1(
            self,
            UpstreamAcquisitionLaneV1.VALIDATION,
        )

    @property
    def upstream_row_evidence_id(self) -> str:
        return _content_id("upstream_row", self._payload())


@dataclass(frozen=True, slots=True)
class DevelopmentUpstreamNovelObservationV1:
    """One replayed prior-validation draw with concrete public semantics."""

    transcript: DevelopmentUpstreamRowTranscriptV1
    accepted_draw_index: int
    bucket: int
    successor_state: DevelopmentPublicStateV1

    def __post_init__(self) -> None:
        if (
            type(self.transcript)
            is not DevelopmentUpstreamRowTranscriptV1
            or self.transcript.semantic_role
            != "PROMOTED_PARENT_ROOT_ROW"
            or type(self.accepted_draw_index) is not int
            or not 0
            <= self.accepted_draw_index
            < self.transcript.validation_draws
            or self.bucket not in (1, 2)
            or type(self.successor_state)
            is not DevelopmentPublicStateV1
            or (
                upstream_raw_word_u64_v1(
                    self.transcript,
                    UpstreamAcquisitionLaneV1.VALIDATION,
                    self.accepted_draw_index,
                )
                & 3
            )
            != self.bucket
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "upstream novel observation is not one replayed bucket mapping"
            )

    @property
    def raw_commitment_id(self) -> str:
        return upstream_raw_commitment_id_v1(
            self.transcript,
            UpstreamAcquisitionLaneV1.VALIDATION,
            self.accepted_draw_index,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_development_multirow_"
                "upstream_novel_observation.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "upstream_row_evidence_id":
                self.transcript.upstream_row_evidence_id,
            "validation_stream_id":
                self.transcript.validation_stream_id,
            "accepted_draw_index": self.accepted_draw_index,
            "raw_commitment_id": self.raw_commitment_id,
            "bucket": self.bucket,
            "successor_state_id": self.successor_state.state_id,
            "successor_ranks": list(self.successor_state.ranks),
            "failure": False,
            "terminal": False,
            "bucket_to_public_semantics_frozen": True,
        }

    @property
    def observation_id(self) -> str:
        return _content_id("upstream_observation", self._payload())


def _upstream_row_transcript(
    *,
    law_key: DevelopmentLawKeyV1,
    arm: str,
    physical_row: DevelopmentPhysicalRowV1,
    semantic_role: str,
) -> DevelopmentUpstreamRowTranscriptV1:
    discovery_seed = _label_id(
        f"upstream-discovery:{law_key.value}:{physical_row.physical_row_id}"
    )
    validation_seed = _label_id(
        f"upstream-validation:{law_key.value}:{physical_row.physical_row_id}"
    )
    discovery_digest, discovery_counts = _upstream_raw_summary(
        discovery_seed,
        UpstreamAcquisitionLaneV1.DISCOVERY,
        CHILD_DISCOVERY_DRAWS,
        law_key,
        semantic_role,
    )
    validation_digest, validation_counts = _upstream_raw_summary(
        validation_seed,
        UpstreamAcquisitionLaneV1.VALIDATION,
        PARENT_VALIDATION_DRAWS,
        law_key,
        semantic_role,
    )
    return DevelopmentUpstreamRowTranscriptV1(
        law_key,
        arm,
        physical_row,
        semantic_role,
        discovery_seed,
        validation_seed,
        discovery_digest,
        validation_digest,
        discovery_counts,
        validation_counts,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentRawObservationStreamV1:
    law_key: DevelopmentLawKeyV1
    arm: str
    logical_occurrence_id: str
    transaction_id: str
    build_epoch_id: str
    context_id: str
    round_index: int
    physical_row_id: str
    parent_stream_id: str | None
    lane: AcquisitionLaneV1
    draw_count: int
    seed_id: str
    crn_pairing_group_seed_id: str
    raw_word_digest: str
    outcome_bucket_counts: tuple[int, int, int, int]

    def __post_init__(self) -> None:
        for value, field in (
            (self.logical_occurrence_id, "stream occurrence"),
            (self.transaction_id, "stream transaction"),
            (self.build_epoch_id, "stream epoch"),
            (self.context_id, "stream context"),
            (self.physical_row_id, "stream row"),
            (self.seed_id, "stream seed"),
            (
                self.crn_pairing_group_seed_id,
                "stream CRN pairing group seed",
            ),
            (self.raw_word_digest, "stream digest"),
        ):
            _cid(value, field)
        expected = {
            AcquisitionLaneV1.PARENT_FRESH_VALIDATION:
                PARENT_VALIDATION_DRAWS,
            AcquisitionLaneV1.CHILD_FRESH_DISCOVERY:
                CHILD_DISCOVERY_DRAWS,
            AcquisitionLaneV1.CHILD_FRESH_VALIDATION:
                CHILD_VALIDATION_DRAWS,
        }.get(self.lane)
        if (
            type(self.law_key) is not DevelopmentLawKeyV1
            or self.arm not in selector.ADAPTIVE_ARMS
            or self.context_id != development_public_context_v1().context_id
            or self.round_index not in (1, 2)
            or self.draw_count != expected
            or sum(self.outcome_bucket_counts) != self.draw_count
            or any(
                type(value) is not int or value < 0
                for value in self.outcome_bucket_counts
            )
            or (
                self.lane is AcquisitionLaneV1.CHILD_FRESH_VALIDATION
            )
            != (self.parent_stream_id is not None)
            or self.seed_id != self.crn_pairing_group_seed_id
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "raw stream lane/count/lineage is invalid"
            )
        if self.parent_stream_id is not None:
            _cid(self.parent_stream_id, "discovery parent stream")
        digest, counts = _raw_summary(
            self.seed_id,
            self.lane,
            self.draw_count,
            self.law_key,
            round_index=self.round_index,
        )
        if digest != self.raw_word_digest or counts != self.outcome_bucket_counts:
            raise V072IncrementalMaterializerInvariantViolation(
                "raw stream does not replay"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_development_multirow_raw_stream.v1",
            "schema_version": SCHEMA_VERSION,
            "law_key": self.law_key.value,
            "arm": self.arm,
            "logical_occurrence_id": self.logical_occurrence_id,
            "transaction_id": self.transaction_id,
            "build_epoch_id": self.build_epoch_id,
            "context_id": self.context_id,
            "round_index": self.round_index,
            "physical_row_id": self.physical_row_id,
            "parent_stream_id": self.parent_stream_id,
            "lane": self.lane.value,
            "draw_count": self.draw_count,
            "seed_id": self.seed_id,
            "crn_pairing_group_seed_id":
                self.crn_pairing_group_seed_id,
            "raw_word_digest": self.raw_word_digest,
            "outcome_bucket_counts": list(self.outcome_bucket_counts),
            "target_endpoint_calls": 0,
            "hidden_law_queries": 0,
        }

    @property
    def stream_id(self) -> str:
        return _content_id("stream", self._payload())


def raw_commitment_id_v1(
    stream: DevelopmentRawObservationStreamV1,
    accepted_draw_index: int,
) -> str:
    """Lazily derive the unique commitment for one accepted raw draw."""

    if (
        type(stream) is not DevelopmentRawObservationStreamV1
        or type(accepted_draw_index) is not int
        or not 0 <= accepted_draw_index < stream.draw_count
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "raw commitment index is outside one exact stream"
        )
    word = _word(
        stream.seed_id,
        stream.lane,
        accepted_draw_index,
        stream.law_key,
        round_index=stream.round_index,
    )
    return _content_id(
        "raw_commitment",
        {
            "schema": (
                "acfqp.v072_development_multirow_raw_commitment.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "stream_id": stream.stream_id,
            "accepted_draw_index": accepted_draw_index,
            "word_u64_hex": f"{word:016x}",
            "accepted_exactly_once": True,
        },
    )


@dataclass(frozen=True, slots=True)
class RawCommitmentRangeProofV1:
    stream_id: str
    draw_count: int
    first_commitment_id: str
    last_commitment_id: str
    ordered_commitment_digest: str
    unique_commitment_count: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.stream_id, "range stream"),
            (self.first_commitment_id, "first raw commitment"),
            (self.last_commitment_id, "last raw commitment"),
            (self.ordered_commitment_digest, "raw commitment digest"),
        ):
            _cid(value, field)
        if (
            type(self.draw_count) is not int
            or self.draw_count <= 0
            or self.unique_commitment_count != self.draw_count
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "raw commitment range cardinality is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_development_multirow_raw_commitment_range.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "stream_id": self.stream_id,
            "accepted_draw_index_range": {
                "first": 0,
                "last": self.draw_count - 1,
            },
            "draw_count": self.draw_count,
            "first_commitment_id": self.first_commitment_id,
            "last_commitment_id": self.last_commitment_id,
            "ordered_commitment_digest":
                self.ordered_commitment_digest,
            "unique_commitment_count": self.unique_commitment_count,
            "complete_contiguous_range": True,
        }

    @property
    def range_proof_id(self) -> str:
        return _content_id("raw_range", self._payload())


def raw_commitment_range_proof_v1(
    stream: DevelopmentRawObservationStreamV1,
) -> RawCommitmentRangeProofV1:
    if type(stream) is not DevelopmentRawObservationStreamV1:
        raise V072IncrementalMaterializerInvariantViolation(
            "range proof requires one exact raw stream"
        )
    digest = hashlib.sha256()
    first = ""
    last = ""
    seen: set[str] = set()
    for index in range(stream.draw_count):
        commitment_id = raw_commitment_id_v1(stream, index)
        if index == 0:
            first = commitment_id
        last = commitment_id
        digest.update(bytes.fromhex(commitment_id))
        seen.add(commitment_id)
    return RawCommitmentRangeProofV1(
        stream.stream_id,
        stream.draw_count,
        first,
        last,
        digest.hexdigest(),
        len(seen),
    )


def upstream_stream_id_v1(
    transcript: DevelopmentUpstreamRowTranscriptV1,
    lane: UpstreamAcquisitionLaneV1,
) -> str:
    """Content identity for one immutable prior-cold raw stream."""

    if (
        type(transcript) is not DevelopmentUpstreamRowTranscriptV1
        or type(lane) is not UpstreamAcquisitionLaneV1
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "upstream stream identity requires exact transcript/lane"
        )
    seed_id = (
        transcript.discovery_seed_id
        if lane is UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_seed_id
    )
    draw_count = (
        transcript.discovery_draws
        if lane is UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_draws
    )
    raw_digest = (
        transcript.discovery_raw_digest
        if lane is UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_raw_digest
    )
    return _content_id(
        "stream",
        {
            "schema": (
                "acfqp.v072_development_multirow_upstream_raw_stream.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "law_key": transcript.law_key.value,
            "arm": transcript.arm,
            "context_id": transcript.physical_row.context_id,
            "physical_row_id":
                transcript.physical_row.physical_row_id,
            "semantic_role": transcript.semantic_role,
            "lane": lane.value,
            "draw_count": draw_count,
            "seed_id": seed_id,
            "crn_pairing_group_seed_id": seed_id,
            "raw_word_digest": raw_digest,
            "created_before_current_authorization": True,
            "incremental_suffix_counter": False,
        },
    )


def upstream_raw_word_u64_v1(
    transcript: DevelopmentUpstreamRowTranscriptV1,
    lane: UpstreamAcquisitionLaneV1,
    accepted_draw_index: int,
) -> int:
    if (
        type(transcript) is not DevelopmentUpstreamRowTranscriptV1
        or type(lane) is not UpstreamAcquisitionLaneV1
        or type(accepted_draw_index) is not int
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "upstream word requires exact transcript/lane/index"
        )
    draw_count = (
        transcript.discovery_draws
        if lane is UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_draws
    )
    if not 0 <= accepted_draw_index < draw_count:
        raise V072IncrementalMaterializerInvariantViolation(
            "upstream word index is outside the immutable range"
        )
    seed_id = (
        transcript.discovery_seed_id
        if lane is UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_seed_id
    )
    return _upstream_word(
        seed_id,
        lane,
        accepted_draw_index,
        transcript.law_key,
        transcript.semantic_role,
    )


def upstream_raw_commitment_id_v1(
    transcript: DevelopmentUpstreamRowTranscriptV1,
    lane: UpstreamAcquisitionLaneV1,
    accepted_draw_index: int,
) -> str:
    word = upstream_raw_word_u64_v1(
        transcript,
        lane,
        accepted_draw_index,
    )
    return _content_id(
        "raw_commitment",
        {
            "schema": (
                "acfqp.v072_development_multirow_raw_commitment.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "stream_id": upstream_stream_id_v1(transcript, lane),
            "accepted_draw_index": accepted_draw_index,
            "word_u64_hex": f"{word:016x}",
            "accepted_exactly_once": True,
        },
    )


def upstream_raw_commitment_range_proof_v1(
    transcript: DevelopmentUpstreamRowTranscriptV1,
    lane: UpstreamAcquisitionLaneV1,
) -> RawCommitmentRangeProofV1:
    if (
        type(transcript) is not DevelopmentUpstreamRowTranscriptV1
        or type(lane) is not UpstreamAcquisitionLaneV1
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "upstream range requires exact transcript/lane"
        )
    draw_count = (
        transcript.discovery_draws
        if lane is UpstreamAcquisitionLaneV1.DISCOVERY
        else transcript.validation_draws
    )
    digest = hashlib.sha256()
    seen: set[str] = set()
    first = ""
    last = ""
    for index in range(draw_count):
        commitment_id = upstream_raw_commitment_id_v1(
            transcript,
            lane,
            index,
        )
        if index == 0:
            first = commitment_id
        last = commitment_id
        digest.update(bytes.fromhex(commitment_id))
        seen.add(commitment_id)
    return RawCommitmentRangeProofV1(
        upstream_stream_id_v1(transcript, lane),
        draw_count,
        first,
        last,
        digest.hexdigest(),
        len(seen),
    )


def raw_word_u64_v1(
    stream: DevelopmentRawObservationStreamV1,
    accepted_draw_index: int,
) -> int:
    """Replay one accepted incremental-suffix raw word."""

    if (
        type(stream) is not DevelopmentRawObservationStreamV1
        or type(accepted_draw_index) is not int
        or not 0 <= accepted_draw_index < stream.draw_count
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "raw word index is outside one exact stream"
        )
    return _word(
        stream.seed_id,
        stream.lane,
        accepted_draw_index,
        stream.law_key,
        round_index=stream.round_index,
    )


def _acquire_stream(
    *,
    law_key: DevelopmentLawKeyV1,
    request: IncrementalMaterializationRequestV1,
    transaction_id: str,
    build_epoch_id: str,
    physical_row_id: str,
    lane: AcquisitionLaneV1,
    parent_stream_id: str | None = None,
) -> DevelopmentRawObservationStreamV1:
    draw_count = {
        AcquisitionLaneV1.PARENT_FRESH_VALIDATION:
            PARENT_VALIDATION_DRAWS,
        AcquisitionLaneV1.CHILD_FRESH_DISCOVERY:
            CHILD_DISCOVERY_DRAWS,
        AcquisitionLaneV1.CHILD_FRESH_VALIDATION:
            CHILD_VALIDATION_DRAWS,
    }[lane]
    seed_id = _label_id(
        "|".join(
            (
                "crn-pairing-group",
                law_key.value,
                request.parent_epoch.context_id,
                str(request.parent_epoch.round_index),
                physical_row_id,
                lane.value,
                (
                    "DISCOVERY_PARENT"
                    if parent_stream_id is not None
                    else "ROOT"
                ),
            )
        )
    )
    digest, counts = _raw_summary(
        seed_id,
        lane,
        draw_count,
        law_key,
        round_index=request.parent_epoch.round_index,
    )
    return DevelopmentRawObservationStreamV1(
        law_key,
        request.parent_epoch.arm,
        request.parent_epoch.logical_occurrence_id,
        transaction_id,
        build_epoch_id,
        request.parent_epoch.context_id,
        request.parent_epoch.round_index,
        physical_row_id,
        parent_stream_id,
        lane,
        draw_count,
        seed_id,
        seed_id,
        digest,
        counts,
    )


@dataclass(frozen=True, slots=True)
class MaterializedChildRowV1:
    physical_row: DevelopmentPhysicalRowV1
    discovery_stream: DevelopmentRawObservationStreamV1
    validation_stream: DevelopmentRawObservationStreamV1

    def __post_init__(self) -> None:
        if (
            type(self.physical_row) is not DevelopmentPhysicalRowV1
            or self.discovery_stream.physical_row_id
            != self.physical_row.physical_row_id
            or self.validation_stream.physical_row_id
            != self.physical_row.physical_row_id
            or self.discovery_stream.lane
            is not AcquisitionLaneV1.CHILD_FRESH_DISCOVERY
            or self.validation_stream.lane
            is not AcquisitionLaneV1.CHILD_FRESH_VALIDATION
            or self.validation_stream.parent_stream_id
            != self.discovery_stream.stream_id
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "child row lacks one fresh 64+8192 stream pair"
            )

    @property
    def row_evidence_id(self) -> str:
        return _content_id(
            "row_evidence",
            {
                "schema": (
                    "acfqp.v072_development_multirow_materialized_row_evidence.v1"
                ),
                "physical_row_id": self.physical_row.physical_row_id,
                "discovery_stream_id": self.discovery_stream.stream_id,
                "validation_stream_id": self.validation_stream.stream_id,
                "discovery_draws": CHILD_DISCOVERY_DRAWS,
                "validation_draws": CHILD_VALIDATION_DRAWS,
            },
        )


@dataclass(frozen=True, slots=True)
class IncrementalNativeCountersV1:
    round_index: int
    acquired_child_rows: int
    parent_discovery_draws: int
    parent_validation_draws: int
    child_discovery_draws: int
    child_validation_draws: int
    observer_calls: int
    random_word_calls: int
    accepted_draws: int
    materializer_calls: int = 1
    target_endpoint_calls: int = 0
    hidden_law_queries: int = 0

    def __post_init__(self) -> None:
        n = self.acquired_child_rows
        exact = PARENT_VALIDATION_DRAWS + CHILD_ROW_DRAWS * n
        if (
            self.round_index not in (1, 2)
            or not 0 <= n <= MAX_CUMULATIVE_CHILD_ROWS
            or self.parent_discovery_draws != 0
            or self.parent_validation_draws != PARENT_VALIDATION_DRAWS
            or self.child_discovery_draws != CHILD_DISCOVERY_DRAWS * n
            or self.child_validation_draws != CHILD_VALIDATION_DRAWS * n
            or self.observer_calls != 1 + 2 * n
            or self.random_word_calls != exact
            or self.accepted_draws != exact
            or self.materializer_calls != 1
            or self.target_endpoint_calls != 0
            or self.hidden_law_queries != 0
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "incremental native counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_incremental_native_counters.v1",
            "round_index": self.round_index,
            "acquired_child_rows": self.acquired_child_rows,
            "parent_discovery_draws": 0,
            "parent_validation_draws": self.parent_validation_draws,
            "child_discovery_draws": self.child_discovery_draws,
            "child_validation_draws": self.child_validation_draws,
            "observer_calls": self.observer_calls,
            "random_word_calls": self.random_word_calls,
            "accepted_draws": self.accepted_draws,
            "materializer_calls": 1,
            "target_endpoint_calls": 0,
            "hidden_law_queries": 0,
        }

    @property
    def counter_id(self) -> str:
        return _content_id("counters", self._payload())


@dataclass(frozen=True, slots=True)
class IncrementalModelRebuildHandoffV1:
    law_key: DevelopmentLawKeyV1
    request: IncrementalMaterializationRequestV1
    transaction_id: str
    build_epoch_id: str
    parent_validation_stream: DevelopmentRawObservationStreamV1
    child_rows: tuple[MaterializedChildRowV1, ...]
    raw_commitment_ranges: tuple[RawCommitmentRangeProofV1, ...]
    counters: IncrementalNativeCountersV1
    resulting_physical_row_ids: tuple[str, ...]
    resulting_physical_row_set_id: str
    status: str = PENDING_STATUS
    model_id: None = None
    selected_policy_id: None = None
    audit_id: None = None
    frontier_id: None = None
    _handoff_id: str = field(
        init=False,
        repr=False,
        compare=False,
    )
    _prior_cold_raw_commitment_ranges: tuple[
        RawCommitmentRangeProofV1, ...
    ] = field(
        init=False,
        repr=False,
        compare=False,
    )

    @property
    def prior_cold_raw_commitment_ranges(
        self,
    ) -> tuple[RawCommitmentRangeProofV1, ...]:
        cached = getattr(
            self,
            "_prior_cold_raw_commitment_ranges",
            None,
        )
        if cached is not None:
            return cached
        values = tuple(
            value
            for transcript in self.request.parent_evidence.upstream_root_rows
            for value in (
                transcript.discovery_raw_commitment_range,
                transcript.validation_raw_commitment_range,
            )
        )
        return tuple(sorted(values, key=lambda item: item.stream_id))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_prior_cold_raw_commitment_ranges",
            self.prior_cold_raw_commitment_ranges,
        )
        for value, field in (
            (self.transaction_id, "handoff transaction"),
            (self.build_epoch_id, "handoff build epoch"),
            (self.resulting_physical_row_set_id, "handoff row set"),
        ):
            _cid(value, field)
        evidence = self.request.cardinality_authority.evidence
        acquired_ids = tuple(
            item.physical_row.physical_row_id for item in self.child_rows
        )
        expected_union = tuple(
            sorted(
                {
                    *self.request.parent_epoch.physical_row_ids,
                    *(
                        item.physical_row_id
                        for item in evidence.cumulative_rows
                    ),
                }
            )
        )
        expected_set_id = _content_id(
            "physical_set",
            {
                "schema": (
                    "acfqp.v072_development_multirow_physical_row_set.v1"
                ),
                "context_id": self.request.parent_epoch.context_id,
                "physical_row_ids": list(expected_union),
            },
        )
        if (
            type(self.law_key) is not DevelopmentLawKeyV1
            or type(self.request) is not IncrementalMaterializationRequestV1
            or self.parent_validation_stream.lane
            is not AcquisitionLaneV1.PARENT_FRESH_VALIDATION
            or self.parent_validation_stream.physical_row_id
            != self.request.parent_evidence.parent_physical_row_id
            or acquired_ids
            != tuple(
                item.physical_row_id for item in evidence.rows_to_acquire
            )
            or type(self.counters) is not IncrementalNativeCountersV1
            or type(self.raw_commitment_ranges) is not tuple
            or any(
                type(item) is not RawCommitmentRangeProofV1
                for item in self.raw_commitment_ranges
            )
            or tuple(
                item.stream_id for item in self.raw_commitment_ranges
            )
            != tuple(
                sorted(
                    {
                        self.parent_validation_stream.stream_id,
                        *(
                            stream.stream_id
                            for child in self.child_rows
                            for stream in (
                                child.discovery_stream,
                                child.validation_stream,
                            )
                        ),
                    }
                )
            )
            or sum(
                item.draw_count for item in self.raw_commitment_ranges
            )
            != self.counters.random_word_calls
            or len(
                {
                    item.stream_id
                    for item in self.prior_cold_raw_commitment_ranges
                }
            )
            != len(self.prior_cold_raw_commitment_ranges)
            or sum(
                item.draw_count
                for item in self.prior_cold_raw_commitment_ranges
            )
            != len(self.request.parent_evidence.upstream_root_rows) * (
                CHILD_DISCOVERY_DRAWS + PARENT_VALIDATION_DRAWS
            )
            or {
                item.stream_id
                for item in self.prior_cold_raw_commitment_ranges
            }
            & {
                item.stream_id for item in self.raw_commitment_ranges
            }
            or self.counters.acquired_child_rows != len(acquired_ids)
            or self.counters.random_word_calls
            != evidence.exact_round_draw_upper
            or self.resulting_physical_row_ids != expected_union
            or self.resulting_physical_row_set_id != expected_set_id
            or self.status != PENDING_STATUS
            or any(
                value is not None
                for value in (
                    self.model_id,
                    self.selected_policy_id,
                    self.audit_id,
                    self.frontier_id,
                )
            )
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "rebuild handoff invents work, rows, or certificate state"
            )
        object.__setattr__(self, "_handoff_id", self.handoff_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_incremental_model_rebuild_handoff.v1",
            "schema_version": SCHEMA_VERSION,
            "law_key": self.law_key.value,
            "request_id": self.request.request_id,
            "authorization_freeze_id":
                self.request.authorization_freeze_id,
            "transaction_id": self.transaction_id,
            "build_epoch_id": self.build_epoch_id,
            "round_index": self.request.parent_epoch.round_index,
            "parent_validation_stream_id":
                self.parent_validation_stream.stream_id,
            "child_row_evidence_ids": [
                item.row_evidence_id for item in self.child_rows
            ],
            "raw_commitment_range_proof_ids": [
                item.range_proof_id
                for item in self.raw_commitment_ranges
            ],
            "prior_cold_raw_commitment_range_proof_ids": [
                item.range_proof_id
                for item in self.prior_cold_raw_commitment_ranges
            ],
            "prior_cold_draws": sum(
                item.draw_count
                for item in self.prior_cold_raw_commitment_ranges
            ),
            "incremental_suffix_draws": self.counters.random_word_calls,
            "prior_cold_work_double_charged": False,
            "counter_id": self.counters.counter_id,
            "resulting_physical_row_ids":
                list(self.resulting_physical_row_ids),
            "resulting_physical_row_set_id":
                self.resulting_physical_row_set_id,
            "status": PENDING_STATUS,
            "model": {"kind": "PENDING_STANDARD_MODEL_REBUILD"},
            "selected_policy": {"kind": "NOT_AVAILABLE"},
            "audit": {"kind": "NOT_RUN"},
            "frontier": {"kind": "NOT_AVAILABLE"},
            "certificate_authority": False,
        }

    @property
    def handoff_id(self) -> str:
        cached = getattr(self, "_handoff_id", None)
        if cached is not None:
            return cached
        return _content_id("handoff", self._payload())


def materialize_authorized_incremental_round_v1(
    *,
    law_key: DevelopmentLawKeyV1,
    request: IncrementalMaterializationRequestV1,
) -> IncrementalModelRebuildHandoffV1:
    """Acquire exactly the rows frozen by the authorization; do not plan."""

    if (
        type(law_key) is not DevelopmentLawKeyV1
        or type(request) is not IncrementalMaterializationRequestV1
    ):
        raise V072IncrementalMaterializerInvariantViolation(
            "materialization requires one development law and exact request"
        )
    transaction_id = _content_id(
        "transaction",
        {
            "schema": "acfqp.v072_incremental_transaction.v1",
            "request_id": request.request_id,
            "authorization_id": request.authorization.authorization_id,
            "round_index": request.parent_epoch.round_index,
            "transaction_index": request.parent_epoch.round_index,
        },
    )
    build_epoch_id = _content_id(
        "epoch",
        {
            "schema": "acfqp.v072_incremental_build_epoch.v1",
            "parent_build_epoch_id": request.parent_epoch.build_epoch_id,
            "parent_model_id": request.parent_epoch.model_id,
            "transaction_id": transaction_id,
            "round_index": request.parent_epoch.round_index,
        },
    )
    parent_stream = _acquire_stream(
        law_key=law_key,
        request=request,
        transaction_id=transaction_id,
        build_epoch_id=build_epoch_id,
        physical_row_id=request.parent_evidence.parent_physical_row_id,
        lane=AcquisitionLaneV1.PARENT_FRESH_VALIDATION,
    )
    child_rows: list[MaterializedChildRowV1] = []
    for row in request.cardinality_authority.evidence.rows_to_acquire:
        discovery = _acquire_stream(
            law_key=law_key,
            request=request,
            transaction_id=transaction_id,
            build_epoch_id=build_epoch_id,
            physical_row_id=row.physical_row_id,
            lane=AcquisitionLaneV1.CHILD_FRESH_DISCOVERY,
        )
        validation = _acquire_stream(
            law_key=law_key,
            request=request,
            transaction_id=transaction_id,
            build_epoch_id=build_epoch_id,
            physical_row_id=row.physical_row_id,
            lane=AcquisitionLaneV1.CHILD_FRESH_VALIDATION,
            parent_stream_id=discovery.stream_id,
        )
        child_rows.append(MaterializedChildRowV1(row, discovery, validation))
    acquired = tuple(child_rows)
    n = len(acquired)
    counters = IncrementalNativeCountersV1(
        request.parent_epoch.round_index,
        n,
        0,
        PARENT_VALIDATION_DRAWS,
        CHILD_DISCOVERY_DRAWS * n,
        CHILD_VALIDATION_DRAWS * n,
        1 + 2 * n,
        PARENT_VALIDATION_DRAWS + CHILD_ROW_DRAWS * n,
        PARENT_VALIDATION_DRAWS + CHILD_ROW_DRAWS * n,
    )
    union = tuple(
        sorted(
            {
                *request.parent_epoch.physical_row_ids,
                *(
                    item.physical_row_id
                    for item in request.cardinality_authority.evidence.cumulative_rows
                ),
            }
        )
    )
    row_set_id = _content_id(
        "physical_set",
        {
            "schema": (
                "acfqp.v072_development_multirow_physical_row_set.v1"
            ),
            "context_id": request.parent_epoch.context_id,
            "physical_row_ids": list(union),
        },
    )
    streams = (
        (parent_stream,)
        + tuple(
            stream
            for child in acquired
            for stream in (
                child.discovery_stream,
                child.validation_stream,
            )
        )
    )
    raw_ranges = tuple(
        sorted(
            (
                raw_commitment_range_proof_v1(stream)
                for stream in streams
            ),
            key=lambda item: item.stream_id,
        )
    )
    return IncrementalModelRebuildHandoffV1(
        law_key,
        request,
        transaction_id,
        build_epoch_id,
        parent_stream,
        acquired,
        raw_ranges,
        counters,
        union,
        row_set_id,
    )


def development_public_context_v1() -> DevelopmentPublicContextV1:
    return DevelopmentPublicContextV1()


def _freeze_development_request(
    law_key: DevelopmentLawKeyV1,
    arm: selector.TargetSelectionArmV2 = (
        selector.TargetSelectionArmV2.NO_PRIOR
    ),
    source_prior: selector.VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None = None,
    logical_occurrence_id: str | None = None,
) -> IncrementalMaterializationRequestV1:
    if type(arm) is not selector.TargetSelectionArmV2:
        raise V072IncrementalMaterializerInvariantViolation(
            "development request arm is not registered"
        )
    selector._prior_resolution(
        arm=arm,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )
    context = development_public_context_v1()
    occurrence_id = (
        _label_id(f"occurrence:{law_key.value}:{arm.value}")
        if logical_occurrence_id is None
        else _cid(logical_occurrence_id, "logical occurrence")
    )
    old_state = DevelopmentPublicStateV1(
        context.context_id,
        (1, 1, 2, 0),
    )
    old_rows = tuple(
        sorted(
            (
                DevelopmentPhysicalRowV1(old_state, action, 2)
                for action in _legal_actions(old_state)
            ),
            key=lambda item: item.physical_row_id,
        )
    )
    upstream_rows = tuple(
        sorted(
            (
                _upstream_row_transcript(
                    law_key=law_key,
                    arm=arm.value,
                    physical_row=row,
                    semantic_role=(
                        "PROMOTED_PARENT_ROOT_ROW"
                        if index == 0
                        else "AUXILIARY_ROOT_ROW"
                    ),
                )
                for index, row in enumerate(old_rows)
            ),
            key=lambda item: item.upstream_row_evidence_id,
        )
    )
    promoted_parent = next(
        item
        for item in upstream_rows
        if item.semantic_role == "PROMOTED_PARENT_ROOT_ROW"
    )
    model_id = _content_id(
        "parent_model",
        {
            "schema": (
                "acfqp.v072_development_multirow_parent_model_snapshot.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": context.context_id,
            "law_key": law_key.value,
            "upstream_root_row_evidence_ids": [
                item.upstream_row_evidence_id for item in upstream_rows
            ],
            "physical_row_ids": [
                item.physical_row.physical_row_id
                for item in upstream_rows
            ],
            "actual_transcript_bound": True,
        },
    )
    closure = DevelopmentCurrentClosureV1(
        context.context_id,
        model_id,
        old_rows,
    )
    epoch = ImmutablePlanningEpochV1(
        occurrence_id,
        context.context_id,
        arm.value,
        1,
        closure.closure_id,
        model_id,
        _label_id(f"failed-audit:{law_key.value}:{arm.value}"),
        _label_id(f"failed-frontier:{law_key.value}:{arm.value}"),
        _label_id("threshold"),
        _label_id(f"selected-plan:{law_key.value}:{arm.value}"),
        _label_id(f"selected-policy:{law_key.value}:{arm.value}"),
        _label_id(f"build-epoch:{law_key.value}:{arm.value}"),
        closure.physical_row_ids,
    )
    novel_states = (
        DevelopmentPublicStateV1(
            context.context_id,
            (1, 1, 2, 3),
        ),
        DevelopmentPublicStateV1(
            context.context_id,
            (3, 2, 1, 1),
        ),
    )
    upstream_novel_observations = tuple(
        DevelopmentUpstreamNovelObservationV1(
            promoted_parent,
            bucket,
            bucket,
            state,
        )
        for bucket, state in zip((1, 2), novel_states)
    )
    descriptors = tuple(
        sorted(
            (
                DevelopmentNovelDescriptorV1(
                    observation.successor_state,
                    (observation.raw_commitment_id,),
                )
                for observation in upstream_novel_observations
            ),
            key=lambda item: item.descriptor_id,
        )
    )
    parent = DevelopmentParentEvidenceV1(
        epoch,
        promoted_parent.physical_row.physical_row_id,
        _label_id(f"support-epoch:{law_key.value}:{arm.value}"),
        _label_id(f"candidate:{law_key.value}:{arm.value}"),
        _label_id(f"planner-row:{law_key.value}:{arm.value}"),
        (_label_id(f"old-support:{law_key.value}:{arm.value}"),),
        descriptors,
        upstream_rows,
        tuple(
            sorted(
                upstream_novel_observations,
                key=lambda item: item.observation_id,
            )
        ),
    )
    evidence = derive_development_cardinality_evidence_v1(
        parent=parent,
        current_closure=closure,
    )
    registry_id = _label_id(f"registry:{law_key.value}:{arm.value}")
    current_slack = Fraction(1, 10)
    counterfactual_slack = Fraction(1, 5)
    gain_value = counterfactual_slack - current_slack
    gain = selector.OneRowCounterfactualGainV2(
        registry_id,
        evidence.selected_candidate_id,
        evidence.model_id,
        evidence.audit_id,
        evidence.frontier_id,
        evidence.threshold_profile_id,
        evidence.support_epoch_id,
        evidence.selected_planner_row_id,
        evidence.exact_round_draw_upper,
        selector.CounterfactualEvaluationStatusV2.EVALUATED,
        _label_id(f"zero-other-model:{law_key.value}:{arm.value}"),
        current_slack,
        counterfactual_slack,
        gain_value,
        gain_value / evidence.exact_round_draw_upper,
        evidence.evidence_id,
    )
    authority = DevelopmentCardinalityAuthorityV1(evidence, gain)
    zeros = tuple(
        selector.NativeZeroPreauthorizationCounterV2(path)
        for path in selector.REQUIRED_NATIVE_ZERO_PATHS
    )
    access = selector.TargetPreauthorizationAccessLogV2(
        registry_id,
        epoch.model_id,
        epoch.audit_id,
        epoch.frontier_id,
        epoch.threshold_profile_id,
        evidence.support_epoch_id,
        1,
        len(evidence.induced_rows),
        len(evidence.induced_rows),
        0,
        zeros,
    )
    schedule_id = _content_id(
        "schedule",
        {
            "schema": "acfqp.v072_development_multirow_schedule.v1",
            "registry_id": registry_id,
            "counterfactual_id": gain.counterfactual_id,
            "selected_candidate_id": evidence.selected_candidate_id,
            "evidence_id": evidence.evidence_id,
        },
    )
    authorization = selector.TargetRowAuthorizationV2(
        registry_id,
        epoch.model_id,
        epoch.audit_id,
        epoch.frontier_id,
        epoch.threshold_profile_id,
        evidence.support_epoch_id,
        (
            None
            if source_prior is None
            else source_prior.source_prior_binding_id
        ),
        (
            None
            if ood_abstention is None
            else ood_abstention.abstention_id
        ),
        arm,
        1,
        schedule_id,
        access.access_log_id,
        evidence.selected_candidate_id,
        evidence.selected_planner_row_id,
        evidence.exact_round_draw_upper,
        len(evidence.cumulative_rows),
        evidence.cumulative_draw_upper,
        1,
        2,
    )
    return IncrementalMaterializationRequestV1(
        epoch,
        parent,
        closure,
        authority,
        access,
        authorization,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentAcquisitionControlRunV1:
    law_key: DevelopmentLawKeyV1
    handoff: IncrementalModelRebuildHandoffV1
    _run_id: str = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.law_key) is not DevelopmentLawKeyV1
            or type(self.handoff) is not IncrementalModelRebuildHandoffV1
            or self.handoff.law_key is not self.law_key
            or self.handoff.status != PENDING_STATUS
            or len(self.handoff.child_rows) != 4
            or self.handoff.counters.random_word_calls
            != PARENT_VALIDATION_DRAWS + 4 * CHILD_ROW_DRAWS
        ):
            raise V072IncrementalMaterializerInvariantViolation(
                "development acquisition control changed"
            )
        object.__setattr__(self, "_run_id", self.run_id)

    @property
    def run_id(self) -> str:
        cached = getattr(self, "_run_id", None)
        if cached is not None:
            return cached
        return _content_id(
            "run",
            {
                "schema": (
                    "acfqp.v072_development_multirow_acquisition_run.v1"
                ),
                "schema_version": SCHEMA_VERSION,
                "law_key": self.law_key.value,
                "arm": self.handoff.request.parent_epoch.arm,
                "handoff_id": self.handoff.handoff_id,
                "status": PENDING_STATUS,
                "registered_target_evidence": False,
                "certificate_authority": False,
                "caller_supplied_result": False,
            },
        )


def run_development_incremental_materializer_control_v1(
    law_key: DevelopmentLawKeyV1,
    arm: selector.TargetSelectionArmV2 = (
        selector.TargetSelectionArmV2.NO_PRIOR
    ),
    source_prior: selector.VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None = None,
    logical_occurrence_id: str | None = None,
) -> DevelopmentAcquisitionControlRunV1:
    """Execute one outcome-blind, real multi-row acquisition transaction."""

    request = _freeze_development_request(
        law_key,
        arm,
        source_prior,
        ood_abstention,
        logical_occurrence_id,
    )
    handoff = materialize_authorized_incremental_round_v1(
        law_key=law_key,
        request=request,
    )
    return DevelopmentAcquisitionControlRunV1(law_key, handoff)


def consume_verified_postbuild_failure_for_round_two_v1(
    *,
    first_handoff: IncrementalModelRebuildHandoffV1,
    failed_postbuild: Any,
    arm: selector.TargetSelectionArmV2 = (
        selector.TargetSelectionArmV2.NO_PRIOR
    ),
    source_prior: selector.VerifiedSourcePriorBindingV2 | None = None,
    ood_abstention: selector.OodPriorTypedAbstentionV2 | None = None,
) -> Any:
    """Consume the installed failed-proof authority and freeze round two."""

    from . import v072_incremental_postbuild_bridge_v1 as postbuild

    return postbuild.prepare_actual_development_round_two_request_v1(
        first_handoff=first_handoff,
        failed_postbuild=failed_postbuild,
        arm=arm,
        source_prior=source_prior,
        ood_abstention=ood_abstention,
    )


def run_registered_v072_incremental_materializer_v1(
    *_args: Any,
    **_kwargs: Any,
) -> None:
    raise RegisteredV072IncrementalMaterializerLocked(
        "registered execution remains locked until the confirmatory manifest "
        "and target authorities are complete"
    )


__all__ = [
    "AcquisitionLaneV1",
    "CHILD_DISCOVERY_DRAWS",
    "CHILD_ROW_DRAWS",
    "CHILD_VALIDATION_DRAWS",
    "DevelopmentAcquisitionControlRunV1",
    "DevelopmentCardinalityAuthorityV1",
    "DevelopmentCardinalityEvidenceV1",
    "DevelopmentCurrentClosureV1",
    "DevelopmentLawKeyV1",
    "DevelopmentNovelDescriptorV1",
    "DevelopmentParentEvidenceV1",
    "DevelopmentPhysicalRowV1",
    "DevelopmentPublicContextV1",
    "DevelopmentPublicStateV1",
    "DevelopmentRawObservationStreamV1",
    "DevelopmentUpstreamRowTranscriptV1",
    "DevelopmentUpstreamNovelObservationV1",
    "ImmutablePlanningEpochV1",
    "IncrementalMaterializationRequestV1",
    "IncrementalModelRebuildHandoffV1",
    "IncrementalNativeCountersV1",
    "MAX_CUMULATIVE_CHILD_ROWS",
    "MAX_CUMULATIVE_DRAWS",
    "MAX_ROUNDS",
    "MaterializedChildRowV1",
    "PARENT_VALIDATION_DRAWS",
    "PENDING_STATUS",
    "POSTBUILD_BRIDGE_INSTALLED",
    "PROPOSED_CONTRACT_VERSION",
    "PostbuildAuthorityNotInstalled",
    "REGISTERED_EXECUTION_ALLOWED",
    "RawCommitmentRangeProofV1",
    "RegisteredV072IncrementalMaterializerLocked",
    "SCHEMA_VERSION",
    "V072IncrementalMaterializerInvariantViolation",
    "UpstreamAcquisitionLaneV1",
    "consume_verified_postbuild_failure_for_round_two_v1",
    "cumulative_draw_upper_v1",
    "derive_development_cardinality_evidence_v1",
    "development_public_context_v1",
    "materialize_authorized_incremental_round_v1",
    "raw_commitment_id_v1",
    "raw_commitment_range_proof_v1",
    "raw_word_u64_v1",
    "run_development_incremental_materializer_control_v1",
    "run_registered_v072_incremental_materializer_v1",
    "upstream_raw_commitment_id_v1",
    "upstream_raw_commitment_range_proof_v1",
    "upstream_raw_word_u64_v1",
    "upstream_stream_id_v1",
]
