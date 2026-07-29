"""Registered failed-proof selector and causal frontier claim for V0-072.

The production entry point accepts only the exact execution chain, adaptive
occurrence plan, failed robust audit, independently replayed registered model
epoch, actual acquisition inventory, and predecessor frontier.  Candidate
rows, causal IDs, scores, statuses, and source quantities are reconstructed
internally.  No observer stream is opened by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from pathlib import Path
from typing import Any, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import heldout_graph_transition_observer_v2 as observer
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp import public_novel_child_cardinality_authority_v2 as descriptors
from acfqp import transfer_guided_acquisition_preregistration_v1 as prereg
from acfqp import verified_source_acquisition_archive_v2 as source_archive
from acfqp import v072_cold_h2_model_builders_v1 as models
from acfqp import (
    v072_cold_h2_model_builders_independent_verifier_v1
    as model_independent,
)
from acfqp import v072_final_preregistration_authority_v1 as final_authority
from acfqp import v072_registered_campaign_consumer_v1 as consumer
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe
from acfqp import (
    v072_registered_target_confidence_accumulator_v1 as accumulator,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_registered_target_selector_v1"
MAX_SELECTED_BOUNDARY_CANDIDATES_PER_ROUND = 1

DOMAIN_TAGS = {
    "generic_candidate": (
        "acfqp:v072-generic-boundary-selector-candidate:v1"
    ),
    "generic_decision": (
        "acfqp:v072-generic-boundary-selector-decision:v1"
    ),
    "new_child": "acfqp:v072-registered-new-child-row-spec:v1",
    "candidate": "acfqp:v072-registered-boundary-candidate:v1",
    "inventory": "acfqp:v072-registered-candidate-inventory:v1",
    "order": "acfqp:v072-registered-proposal-order:v1",
    "claim": "acfqp:v072-registered-selector-claim:v1",
    "closure": "acfqp:v072-registered-selector-closure:v1",
}


class V072RegisteredTargetSelectorInvariantViolation(ValueError):
    """A proof, model epoch, candidate, order, cap, or identity differs."""


class RegisteredSelectorGateLockedV1(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        observer_stream_opens: int = 0,
        observer_draw_calls: int = 0,
    ) -> None:
        super().__init__(message)
        self.observer_stream_opens = observer_stream_opens
        self.observer_draw_calls = observer_draw_calls


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V072RegisteredTargetSelectorInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072RegisteredTargetSelectorInvariantViolation(
            f"{label} must be one full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072RegisteredTargetSelectorInvariantViolation(
            "registered selector requires exact Fraction values"
        )
    return {"numerator": value.numerator, "denominator": value.denominator}


def _fraction_document(value: Any, label: str) -> Fraction:
    if (
        type(value) is not dict
        or set(value) != {"numerator", "denominator"}
        or type(value["numerator"]) is not int
        or type(value["denominator"]) is not int
        or value["denominator"] <= 0
    ):
        raise V072RegisteredTargetSelectorInvariantViolation(
            f"{label} is not one reduced rational document"
        )
    result = Fraction(value["numerator"], value["denominator"])
    if (
        result.numerator != value["numerator"]
        or result.denominator != value["denominator"]
    ):
        raise V072RegisteredTargetSelectorInvariantViolation(
            f"{label} is not reduced"
        )
    return result


class RegisteredSelectorOutcomeV1(str, Enum):
    SELECTED = "SELECTED"
    NO_SOUND_COVER = "NO_SOUND_COVER"
    CAP_EXHAUSTED = "CAP_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class GenericBoundaryCandidateV1:
    candidate_id: str
    boundary_depth: int
    physical_row_binding_ids: tuple[str, ...]
    causal_weight: Fraction
    draw_upper: int
    source_midrank: Fraction | None
    sound_cover: bool = True
    cap_eligible: bool = True
    _generic_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.candidate_id, "generic candidate")
        for item in self.physical_row_binding_ids:
            _cid(item, "generic physical row")
        if (
            self.boundary_depth not in (0, 1)
            or self.physical_row_binding_ids
            != tuple(sorted(set(self.physical_row_binding_ids)))
            or not self.physical_row_binding_ids
            or type(self.causal_weight) is not Fraction
            or self.causal_weight < 0
            or type(self.draw_upper) is not int
            or self.draw_upper <= 0
            or (
                self.source_midrank is not None
                and (
                    type(self.source_midrank) is not Fraction
                    or not 0 <= self.source_midrank <= 1
                )
            )
            or type(self.sound_cover) is not bool
            or type(self.cap_eligible) is not bool
        ):
            raise V072RegisteredTargetSelectorInvariantViolation(
                "generic selector candidate is malformed"
            )
        object.__setattr__(
            self,
            "_generic_id",
            _content_id("generic_candidate", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_generic_boundary_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_id": self.candidate_id,
            "boundary_depth": self.boundary_depth,
            "physical_row_binding_ids": list(
                self.physical_row_binding_ids
            ),
            "causal_weight": _fdoc(self.causal_weight),
            "draw_upper": self.draw_upper,
            "source_midrank": (
                None
                if self.source_midrank is None
                else _fdoc(self.source_midrank)
            ),
            "sound_cover": self.sound_cover,
            "cap_eligible": self.cap_eligible,
            "source_can_change_legality": False,
        }

    @property
    def generic_id(self) -> str:
        return self._generic_id


@dataclass(frozen=True, slots=True)
class GenericBoundarySelectionDecisionV1:
    arm: str
    remaining_draw_cap: int
    candidate_ids: tuple[str, ...]
    ordered_eligible_candidate_ids: tuple[str, ...]
    outcome: RegisteredSelectorOutcomeV1
    selected_candidate_id: str | None
    _decision_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for item in (
            *self.candidate_ids,
            *self.ordered_eligible_candidate_ids,
        ):
            _cid(item, "generic decision candidate")
        if self.selected_candidate_id is not None:
            _cid(self.selected_candidate_id, "generic selected candidate")
        if (
            self.arm not in prereg.ARM_ORDER[:-1]
            or type(self.remaining_draw_cap) is not int
            or self.remaining_draw_cap < 0
            or self.candidate_ids
            != tuple(sorted(set(self.candidate_ids)))
            or len(set(self.ordered_eligible_candidate_ids))
            != len(self.ordered_eligible_candidate_ids)
            or not set(self.ordered_eligible_candidate_ids).issubset(
                self.candidate_ids
            )
            or type(self.outcome) is not RegisteredSelectorOutcomeV1
            or (
                self.outcome is RegisteredSelectorOutcomeV1.SELECTED
                and (
                    not self.ordered_eligible_candidate_ids
                    or self.selected_candidate_id
                    != self.ordered_eligible_candidate_ids[0]
                )
            )
            or (
                self.outcome is not RegisteredSelectorOutcomeV1.SELECTED
                and self.selected_candidate_id is not None
            )
        ):
            raise V072RegisteredTargetSelectorInvariantViolation(
                "generic selector decision does not reconcile"
            )
        object.__setattr__(
            self,
            "_decision_id",
            _content_id("generic_decision", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_generic_boundary_selection_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "arm": self.arm,
            "remaining_draw_cap": self.remaining_draw_cap,
            "candidate_ids": list(self.candidate_ids),
            "ordered_eligible_candidate_ids": list(
                self.ordered_eligible_candidate_ids
            ),
            "outcome": self.outcome.value,
            "selected_candidate_id": self.selected_candidate_id,
            "deterministic_tie_break": (
                "EARLIEST_BOUNDARY_THEN_SCORE_GAIN_DRAW_ID"
            ),
            "maximum_selected_candidates": 1,
            "source_changes_legality": False,
        }

    @property
    def decision_id(self) -> str:
        return self._decision_id


def select_generic_boundary_candidate_core_v1(
    *,
    candidates: tuple[GenericBoundaryCandidateV1, ...],
    arm: str,
    remaining_draw_cap: int,
) -> GenericBoundarySelectionDecisionV1:
    """Registration-disjoint deterministic selection and typed closures."""

    if (
        type(candidates) is not tuple
        or any(type(item) is not GenericBoundaryCandidateV1 for item in candidates)
        or tuple(item.candidate_id for item in candidates)
        != tuple(sorted({item.candidate_id for item in candidates}))
        or arm not in prereg.ARM_ORDER[:-1]
        or type(remaining_draw_cap) is not int
        or remaining_draw_cap < 0
    ):
        raise V072RegisteredTargetSelectorInvariantViolation(
            "generic selector input is outside the frozen profile"
        )
    sound = tuple(
        item
        for item in candidates
        if item.sound_cover and item.causal_weight > 0
    )
    if not sound:
        return GenericBoundarySelectionDecisionV1(
            arm,
            remaining_draw_cap,
            tuple(item.candidate_id for item in candidates),
            (),
            RegisteredSelectorOutcomeV1.NO_SOUND_COVER,
            None,
        )
    eligible = tuple(
        item
        for item in sound
        if item.cap_eligible and item.draw_upper <= remaining_draw_cap
    )
    if not eligible:
        return GenericBoundarySelectionDecisionV1(
            arm,
            remaining_draw_cap,
            tuple(item.candidate_id for item in candidates),
            (),
            RegisteredSelectorOutcomeV1.CAP_EXHAUSTED,
            None,
        )

    def multiplier(item: GenericBoundaryCandidateV1) -> Fraction:
        if (
            arm
            in ("SOURCE_CONSENSUS_PRIOR", "WRONG_CONSENSUS_PRIOR")
            and item.source_midrank is not None
        ):
            q = (
                item.source_midrank
                if arm == "SOURCE_CONSENSUS_PRIOR"
                else 1 - item.source_midrank
            )
            return Fraction(1, 2) + Fraction(3, 2) * q
        return Fraction(1)

    ordered = tuple(
        item.candidate_id
        for item in sorted(
            eligible,
            key=lambda item: (
                item.boundary_depth,
                -(item.causal_weight / item.draw_upper * multiplier(item)),
                -item.causal_weight,
                item.draw_upper,
                item.candidate_id,
            ),
        )
    )
    return GenericBoundarySelectionDecisionV1(
        arm,
        remaining_draw_cap,
        tuple(item.candidate_id for item in candidates),
        ordered,
        RegisteredSelectorOutcomeV1.SELECTED,
        ordered[0],
    )


@dataclass(frozen=True, slots=True)
class RegisteredNewChildRowSpecV1:
    source_parent_row_binding_id: str
    source_descriptor_ids: tuple[str, ...]
    catalogue: observer.HeldoutLegalActionCatalogueV2
    action: tuple[int, int, int]
    row_binding_id: str
    _spec_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        _cid(self.source_parent_row_binding_id, "new-child parent row")
        _cid(self.row_binding_id, "new-child row")
        for item in self.source_descriptor_ids:
            _cid(item, "new-child source descriptor")
        if (
            self.source_descriptor_ids
            != tuple(sorted(set(self.source_descriptor_ids)))
            or not self.source_descriptor_ids
            or type(self.catalogue)
            is not observer.HeldoutLegalActionCatalogueV2
            or self.catalogue.remaining_horizon != 1
            or self.action not in self.catalogue.actions
        ):
            raise V072RegisteredTargetSelectorInvariantViolation(
                "new-child row spec is incomplete"
            )
        object.__setattr__(
            self,
            "_spec_id",
            _content_id("new_child", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_new_child_row_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "source_parent_row_binding_id": (
                self.source_parent_row_binding_id
            ),
            "source_descriptor_ids": list(self.source_descriptor_ids),
            "catalogue_id": self.catalogue.catalogue_id,
            "action": list(self.action),
            "row_binding_id": self.row_binding_id,
            "complete_public_catalogue": True,
            "caller_candidate": False,
        }

    @property
    def spec_id(self) -> str:
        return self._spec_id


_CANDIDATE_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredBoundaryCandidateV1:
    _minting_capability: object
    planner_row_id: str
    source_row_id: str
    projection_id: str
    parent_acquisition_id: str
    promotion_row_binding_id: str
    new_child_rows: tuple[RegisteredNewChildRowSpecV1, ...]
    portable_feature_key: str
    source_midrank: Fraction | None
    boundary_depth: int
    causal_weight: Fraction
    sound_cover: bool
    cap_eligible: bool
    draw_upper: int
    _candidate_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.planner_row_id,
            self.source_row_id,
            self.projection_id,
            self.parent_acquisition_id,
            self.promotion_row_binding_id,
            self.portable_feature_key,
        ):
            _cid(value, "registered boundary candidate identity")
        if (
            self._minting_capability is not _CANDIDATE_MINTING_SENTINEL
            or type(self.new_child_rows) is not tuple
            or any(
                type(item) is not RegisteredNewChildRowSpecV1
                for item in self.new_child_rows
            )
            or tuple(item.row_binding_id for item in self.new_child_rows)
            != tuple(
                sorted({item.row_binding_id for item in self.new_child_rows})
            )
            or any(
                item.source_parent_row_binding_id
                != self.promotion_row_binding_id
                for item in self.new_child_rows
            )
            or (
                self.source_midrank is not None
                and (
                    type(self.source_midrank) is not Fraction
                    or not 0 <= self.source_midrank <= 1
                )
            )
            or self.boundary_depth not in (0, 1)
            or type(self.causal_weight) is not Fraction
            or self.causal_weight < 0
            or type(self.sound_cover) is not bool
            or type(self.cap_eligible) is not bool
            or self.draw_upper
            != (
                prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
                + (
                    prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
                    + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
                )
                * len(self.new_child_rows)
            )
        ):
            raise V072RegisteredTargetSelectorInvariantViolation(
                "registered boundary candidate is malformed"
            )
        object.__setattr__(
            self,
            "_candidate_id",
            _content_id("candidate", self._payload()),
        )

    @property
    def selected_row_binding_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                (
                    self.promotion_row_binding_id,
                    *(item.row_binding_id for item in self.new_child_rows),
                )
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_boundary_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "planner_row_id": self.planner_row_id,
            "source_row_id": self.source_row_id,
            "projection_id": self.projection_id,
            "parent_acquisition_id": self.parent_acquisition_id,
            "promotion_row_binding_id": self.promotion_row_binding_id,
            "new_child_spec_ids": [
                item.spec_id for item in self.new_child_rows
            ],
            "selected_row_binding_ids": list(
                self.selected_row_binding_ids
            ),
            "portable_feature_key": self.portable_feature_key,
            "boundary_depth": self.boundary_depth,
            "causal_weight": _fdoc(self.causal_weight),
            "sound_cover": self.sound_cover,
            "cap_eligible": self.cap_eligible,
            "draw_upper": self.draw_upper,
            "source_changes_legality": False,
            "source_quantity_serialized": False,
            "caller_candidate": False,
        }

    @property
    def candidate_id(self) -> str:
        return self._candidate_id

    def generic(self) -> GenericBoundaryCandidateV1:
        return GenericBoundaryCandidateV1(
            self.candidate_id,
            self.boundary_depth,
            self.selected_row_binding_ids,
            self.causal_weight,
            self.draw_upper,
            self.source_midrank,
            self.sound_cover,
            self.cap_eligible,
        )


_CLAIM_MINTING_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredSelectorClaimV1:
    _minting_capability: object
    authority_chain_id: str
    anchor_id: str
    occurrence_id: str
    context_id: str
    arm: str
    round_index: int
    predecessor_frontier_id: str | None
    failed_audit_id: str
    failed_frontier_id: str
    model_pair_id: str
    model_replay_attestation_id: str
    supporting_acquisition_ids: tuple[str, ...]
    supporting_row_binding_ids: tuple[str, ...]
    candidates: tuple[RegisteredBoundaryCandidateV1, ...]
    source_recipe_id: str | None
    decision: GenericBoundarySelectionDecisionV1
    cumulative_draw_upper_before_round: int
    _candidate_inventory_id: str = field(init=False, repr=False)
    _proposal_order_id: str = field(init=False, repr=False)
    _claim_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value in (
            self.authority_chain_id,
            self.anchor_id,
            self.occurrence_id,
            self.context_id,
            self.failed_audit_id,
            self.failed_frontier_id,
            self.model_pair_id,
            self.model_replay_attestation_id,
            *self.supporting_acquisition_ids,
            *self.supporting_row_binding_ids,
        ):
            _cid(value, "registered selector claim identity")
        if self.predecessor_frontier_id is not None:
            _cid(self.predecessor_frontier_id, "selector predecessor")
        if self.source_recipe_id is not None:
            _cid(self.source_recipe_id, "selector source recipe")
        if (
            self._minting_capability is not _CLAIM_MINTING_SENTINEL
            or self.arm not in prereg.ARM_ORDER[:-1]
            or self.round_index not in (1, 2)
            or (
                self.round_index == 1
                and (
                    self.predecessor_frontier_id is not None
                    or self.cumulative_draw_upper_before_round != 0
                )
            )
            or (
                self.round_index == 2
                and (
                    self.predecessor_frontier_id is None
                    or self.cumulative_draw_upper_before_round <= 0
                )
            )
            or self.supporting_acquisition_ids
            != tuple(sorted(set(self.supporting_acquisition_ids)))
            or not self.supporting_acquisition_ids
            or self.supporting_row_binding_ids
            != tuple(sorted(set(self.supporting_row_binding_ids)))
            or not self.supporting_row_binding_ids
            or self.candidates
            != tuple(sorted(self.candidates, key=lambda item: item.candidate_id))
            or len({item.candidate_id for item in self.candidates})
            != len(self.candidates)
            or type(self.decision)
            is not GenericBoundarySelectionDecisionV1
            or self.decision.arm != self.arm
            or self.decision.candidate_ids
            != tuple(item.candidate_id for item in self.candidates)
            or (
                self.arm
                in ("SOURCE_CONSENSUS_PRIOR", "WRONG_CONSENSUS_PRIOR")
            )
            != (self.source_recipe_id is not None)
        ):
            raise V072RegisteredTargetSelectorInvariantViolation(
                "registered selector claim is not canonical"
            )
        object.__setattr__(
            self,
            "_candidate_inventory_id",
            _content_id(
                "inventory",
                {
                    "schema": (
                        "acfqp.v072_registered_candidate_inventory.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "failed_frontier_id": self.failed_frontier_id,
                    "model_pair_id": self.model_pair_id,
                    "supporting_acquisition_ids": list(
                        self.supporting_acquisition_ids
                    ),
                    "candidate_ids": [
                        item.candidate_id for item in self.candidates
                    ],
                    "caller_candidates_accepted": False,
                },
            ),
        )
        object.__setattr__(
            self,
            "_proposal_order_id",
            _content_id(
                "order",
                {
                    "schema": (
                        "acfqp.v072_registered_proposal_order.v1"
                    ),
                    "schema_version": SCHEMA_VERSION,
                    "candidate_inventory_id": self.candidate_inventory_id,
                    "arm": self.arm,
                    "source_recipe_id": self.source_recipe_id,
                    "decision_id": self.decision.decision_id,
                    "source_used_for_ordering_only": True,
                },
            ),
        )
        object.__setattr__(
            self,
            "_claim_id",
            _content_id("claim", self._payload()),
        )

    @property
    def candidate_inventory_id(self) -> str:
        return self._candidate_inventory_id

    @property
    def proposal_order_id(self) -> str:
        return self._proposal_order_id

    @property
    def selected_candidate(self) -> RegisteredBoundaryCandidateV1 | None:
        if self.decision.selected_candidate_id is None:
            return None
        return {
            item.candidate_id: item for item in self.candidates
        }[self.decision.selected_candidate_id]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_selector_claim.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "authority_chain_id": self.authority_chain_id,
            "anchor_id": self.anchor_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "arm": self.arm,
            "round_index": self.round_index,
            "predecessor_frontier_id": self.predecessor_frontier_id,
            "failed_audit_id": self.failed_audit_id,
            "failed_frontier_id": self.failed_frontier_id,
            "model_pair_id": self.model_pair_id,
            "model_replay_attestation_id": (
                self.model_replay_attestation_id
            ),
            "supporting_acquisition_ids": list(
                self.supporting_acquisition_ids
            ),
            "supporting_row_binding_ids": list(
                self.supporting_row_binding_ids
            ),
            "candidate_inventory_id": self.candidate_inventory_id,
            "proposal_order_id": self.proposal_order_id,
            "source_recipe_id": self.source_recipe_id,
            "decision_id": self.decision.decision_id,
            "outcome": self.decision.outcome.value,
            "selected_candidate_id": self.decision.selected_candidate_id,
            "cumulative_draw_upper_before_round": (
                self.cumulative_draw_upper_before_round
            ),
            "source_used_in_confidence_or_certificate": False,
            "caller_candidate_or_status_accepted": False,
            "observer_stream_opens": 0,
            "observer_draw_calls": 0,
        }

    @property
    def claim_id(self) -> str:
        return self._claim_id


def _count_bin(value: int) -> str:
    if value <= 0:
        return "0"
    if value == 1:
        return "1"
    if value == 2:
        return "2"
    return "3_PLUS"


def _portable_feature(
    model: robust.PartialSupportIntervalModelV1,
    audit: robust.RobustPlanAuditV1,
    row: robust.IntervalSimplexRowV1,
) -> source_archive.PortableAcquisitionCoreFeatureV2:
    provenance = {
        item.row_id: item for item in audit.selected_row_provenance
    }.get(row.row_id)
    catalogue = {
        item.state_id: item for item in model.catalogues
    }.get(row.state_id)
    assignments = {
        (item.scope_key, item.remaining_horizon): item.selected_action_key
        for item in audit.assignments
    }
    if provenance is None or catalogue is None:
        raise V072RegisteredTargetSelectorInvariantViolation(
            "failed row lacks selected-policy provenance/catalogue"
        )
    selected_action = assignments.get(
        (provenance.policy_scope_key, row.remaining_horizon)
    )
    if selected_action is None:
        raise V072RegisteredTargetSelectorInvariantViolation(
            "failed row is not in the selected policy"
        )
    sizes = {
        len(item.ground_action_ids)
        for item in model.concretizer_entries
        if (
            item.state_id == row.state_id
            and item.abstract_action_key == selected_action
        )
    }
    if len(sizes) != 1:
        raise V072RegisteredTargetSelectorInvariantViolation(
            "failed quotient action lacks one concretizer cardinality"
        )
    destination_by_id = {
        item.destination_id: item for item in model.destinations
    }
    categories = tuple(
        sorted(
            {
                destination_by_id[item.destination_id].category.value
                for item in row.masses
                if item.destination_id != row.other_destination_id
            }
        )
    )
    return source_archive.PortableAcquisitionCoreFeatureV2(
        "ROOT" if row.remaining_horizon == 2 else "CONTINUATION",
        provenance.category.value,
        _count_bin(len(catalogue.actions)),
        _count_bin(next(iter(sizes))),
        categories,
    )


def _source_midrank_by_feature(
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    arm: str,
) -> tuple[str | None, dict[str, Fraction]]:
    if arm not in (
        "SOURCE_CONSENSUS_PRIOR",
        "WRONG_CONSENSUS_PRIOR",
    ):
        return None, {}
    claim = authority_chain.remote_main_anchor.claim
    path = (
        Path(authority_chain.repository_root)
        / claim.source_reconstruction_recipe_repository_path
    )
    recipe = source_recipe.load_source_reconstruction_recipe_v1(path)
    if recipe.recipe_id != claim.source_reconstruction_recipe_id:
        raise RegisteredSelectorGateLockedV1(
            "source proposal recipe is stale",
        )
    document = recipe.to_document()
    archive_document = document["compact_derived_artifacts"][
        "source_archive"
    ]
    consensus = archive_document["consensus"]
    values: dict[str, Fraction] = {}
    for item in consensus:
        if item["disposition"] == "APPLIED":
            values[_cid(item["feature_key"], "source feature")] = (
                _fraction_document(
                    item["mean_midrank"],
                    "source mean midrank",
                )
            )
    return recipe.recipe_id, values


def _descriptor_id(
    observation: observer.HeldoutObservedJointTransitionV2,
) -> str:
    return descriptors.RecordedTransitionDescriptorV2(
        observation.next_state,
        observation.realized_row_reward,
        observation.failure,
        observation.terminal,
    ).descriptor_id


def _new_child_rows(
    *,
    context: prereg.HeldoutPublicGraphContextV2,
    parent: accumulator.RegisteredTargetRowAcquisitionV1,
    existing_rows: set[str],
) -> tuple[RegisteredNewChildRowSpecV1, ...]:
    by_state: dict[str, tuple[observer.HeldoutSymbolicGraphStateV2, set[str]]] = {}
    novel = set(parent.validation_novel_descriptor_ids)
    for observation in parent.transcript.validation_observations:
        descriptor_id = _descriptor_id(observation)
        if (
            descriptor_id not in novel
            or observation.failure
            or observation.terminal
            or observation.remaining_horizon != 2
        ):
            continue
        entry = by_state.setdefault(
            observation.next_state.state_id,
            (observation.next_state, set()),
        )
        entry[1].add(descriptor_id)
    by_row: dict[str, RegisteredNewChildRowSpecV1] = {}
    for state, source_ids in by_state.values():
        catalogue = observer.legal_action_catalogue_v2(context, state, 1)
        for action in catalogue.actions:
            binding = observer.observation_row_binding_v2(
                context,
                catalogue,
                action,
            )
            if binding.row_binding_id in existing_rows:
                continue
            spec = RegisteredNewChildRowSpecV1(
                parent.row_binding_id,
                tuple(sorted(source_ids)),
                catalogue,
                action,
                binding.row_binding_id,
            )
            by_row[binding.row_binding_id] = spec
    return tuple(sorted(by_row.values(), key=lambda item: item.row_binding_id))


def _validate_inputs(
    *,
    authority_chain: Any,
    anchor: Any,
    occurrence_plan: Any,
    failed_audit: Any,
    model_pair: Any,
    model_replay_attestation: Any,
    acquisitions: Any,
    round_index: Any,
    predecessor_frontier: Any,
) -> None:
    if (
        type(authority_chain)
        is not consumer.RegisteredCampaignAuthorityChainV1
        or type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or authority_chain.remote_main_anchor is not anchor
        or type(occurrence_plan)
        is not consumer.RegisteredOccurrenceExecutionPlanV1
        or type(failed_audit) is not robust.RobustPlanAuditV1
        or type(model_pair) is not models.RegisteredColdH2ModelPairV1
        or type(model_replay_attestation)
        is not (
            model_independent
            .RegisteredColdH2ModelIndependentReplayAttestationV1
        )
        or type(acquisitions) is not tuple
        or not acquisitions
        or any(
            type(item)
            is not accumulator.RegisteredTargetRowAcquisitionV1
            for item in acquisitions
        )
        or round_index not in (1, 2)
    ):
        raise RegisteredSelectorGateLockedV1(
            "registered selector requires exact typed production inputs"
        )
    try:
        consumer.verify_registered_campaign_authority_chain_v1(
            authority_chain
        )
    except (ValueError, consumer.RegisteredCampaignAuthorityGateLockedV1) as error:
        raise RegisteredSelectorGateLockedV1(
            "registered selector authority chain is stale"
        ) from error
    template = occurrence_plan.template
    if (
        occurrence_plan.chain_id != authority_chain.chain_id
        or template.route_kind
        is not consumer.RegisteredRouteKindV1.ADAPTIVE_QUOTIENT
        or template.context_id != model_pair.closure_bundle.context_id
        or template.arm not in prereg.ARM_ORDER[:-1]
        or model_pair.anchor_id != anchor.anchor_id
        or model_pair.final_preregistration_id
        != anchor.claim.final_preregistration_id
        or model_replay_attestation.model_pair_id
        != model_pair.model_pair_id
        or model_replay_attestation.remote_main_anchor_id
        != anchor.anchor_id
        or model_replay_attestation.remote_main_anchor_attestation_id
        != authority_chain.remote_main_anchor_attestation.verification_id
        or failed_audit.model_id
        != model_pair.quotient_planner_model.model_id
        or failed_audit.threshold_profile_id
        != model_pair.threshold_profile.threshold_profile_id
        or failed_audit.status
        is not robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
        or failed_audit.failed_frontier is None
    ):
        raise RegisteredSelectorGateLockedV1(
            "registered occurrence/proof/model epoch is rebound"
        )
    replayed_model = (
        model_independent
        .verify_registered_cold_h2_model_pair_independently_v1(
            anchor,
            authority_chain.remote_main_anchor_attestation,
            model_pair,
        )
    )
    if replayed_model.to_document() != model_replay_attestation.to_document():
        raise RegisteredSelectorGateLockedV1(
            "registered model epoch independent replay differs"
        )
    robust.verify_robust_plan_audit_v1(
        model_pair.quotient_planner_model,
        model_pair.threshold_profile,
        failed_audit,
    )
    acquisition_ids = tuple(
        sorted(item.acquisition_id for item in acquisitions)
    )
    if (
        acquisition_ids
        != tuple(item.acquisition_id for item in acquisitions)
        or len(set(acquisition_ids)) != len(acquisition_ids)
        or any(
            item.authority_chain_id != authority_chain.chain_id
            or item.anchor_id != anchor.anchor_id
            or item.context.context_id != template.context_id
            or item.arm != template.arm
            for item in acquisitions
        )
    ):
        raise RegisteredSelectorGateLockedV1(
            "actual acquisition inventory is reordered or foreign"
        )
    if round_index == 1:
        if predecessor_frontier is not None:
            raise RegisteredSelectorGateLockedV1(
                "round one cannot bind a predecessor frontier"
            )
    elif (
        type(predecessor_frontier)
        is not accumulator.RegisteredAcquisitionFrontierV1
        or predecessor_frontier.round_index != 1
        or predecessor_frontier.authority_chain_id
        != authority_chain.chain_id
        or predecessor_frontier.anchor_id != anchor.anchor_id
        or predecessor_frontier.context_id != template.context_id
        or predecessor_frontier.arm != template.arm
        or not set(predecessor_frontier.supporting_acquisition_ids)
        < set(acquisition_ids)
    ):
        raise RegisteredSelectorGateLockedV1(
            "round two lacks a fresh strict acquisition extension"
        )


def _build_claim(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    failed_audit: robust.RobustPlanAuditV1,
    model_pair: models.RegisteredColdH2ModelPairV1,
    model_replay_attestation: (
        model_independent.RegisteredColdH2ModelIndependentReplayAttestationV1
    ),
    acquisitions: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ],
    round_index: int,
    predecessor_frontier: (
        accumulator.RegisteredAcquisitionFrontierV1 | None
    ),
) -> RegisteredSelectorClaimV1:
    model = model_pair.quotient_planner_model
    frontier = failed_audit.failed_frontier
    assert frontier is not None
    planner_to_source = {
        planner_row_id: source_row_id
        for source_row_id, _other_id, planner_row_id
        in model_pair.quotient_collapse_proof.row_mappings
    }
    projection_by_source = {
        item.interval_row.row_id: item for item in model_pair.row_projections
    }
    acquisition_by_transcript = {
        item.transcript.transcript_id: item for item in acquisitions
    }
    existing_rows = {item.row_binding_id for item in acquisitions}
    source_recipe_id, source_midrank = _source_midrank_by_feature(
        authority_chain,
        occurrence_plan.template.arm,
    )
    previous_draws = (
        0
        if predecessor_frontier is None
        else predecessor_frontier.cumulative_draw_upper
    )
    previous_new_children = (
        set()
        if predecessor_frontier is None
        else set(predecessor_frontier.new_child_row_binding_ids)
    )
    remaining_draw_cap = (
        prereg.MAX_TWO_ROUND_INCREMENTAL_DRAW_CAP_PER_ARM
        - previous_draws
    )
    row_by_id = {item.row_id: item for item in model.rows}
    output: list[RegisteredBoundaryCandidateV1] = []
    for planner_row_id in frontier.other_positive_row_ids:
        source_row_id = planner_to_source.get(planner_row_id)
        projection = (
            None
            if source_row_id is None
            else projection_by_source.get(source_row_id)
        )
        row = row_by_id.get(planner_row_id)
        if projection is None or row is None:
            raise RegisteredSelectorGateLockedV1(
                "failed frontier row has no registered physical projection"
            )
        parent = acquisition_by_transcript.get(
            projection.validation_transcript_id
        )
        if (
            parent is None
            or parent.row_binding_id
            != projection.row_evidence.action.semantic_action_id
        ):
            raise RegisteredSelectorGateLockedV1(
                "failed physical row lacks its actual acquisition"
            )
        new_rows = _new_child_rows(
            context=parent.context,
            parent=parent,
            existing_rows=existing_rows,
        )
        feature = _portable_feature(model, failed_audit, row)
        causal_weight = row.other_mass.upper
        sound_cover = (
            frontier.other_only_counterfactual_changes
            and causal_weight > 0
            and parent.round_index == round_index - 1
        )
        union_new = previous_new_children | {
            item.row_binding_id for item in new_rows
        }
        draw_upper = (
            prereg.PROMOTION_VALIDATION_DRAWS_PER_ROUND
            + (
                prereg.NEW_CHILD_DISCOVERY_DRAWS_PER_PHYSICAL_ROW
                + prereg.NEW_CHILD_VALIDATION_DRAWS_PER_PHYSICAL_ROW
            )
            * len(new_rows)
        )
        cap_eligible = (
            len(union_new)
            <= prereg.MAX_NEW_CHILD_ACTION_ROWS_ACROSS_ROUNDS
            and draw_upper <= remaining_draw_cap
        )
        output.append(
            RegisteredBoundaryCandidateV1(
                _CANDIDATE_MINTING_SENTINEL,
                planner_row_id,
                source_row_id,
                projection.projection_id,
                parent.acquisition_id,
                parent.row_binding_id,
                new_rows,
                feature.feature_key,
                source_midrank.get(feature.feature_key),
                2 - row.remaining_horizon,
                causal_weight,
                sound_cover,
                cap_eligible,
                draw_upper,
            )
        )
    candidates = tuple(
        sorted(output, key=lambda item: item.candidate_id)
    )
    decision = select_generic_boundary_candidate_core_v1(
        candidates=tuple(item.generic() for item in candidates),
        arm=occurrence_plan.template.arm,
        remaining_draw_cap=remaining_draw_cap,
    )
    return RegisteredSelectorClaimV1(
        _CLAIM_MINTING_SENTINEL,
        authority_chain.chain_id,
        anchor.anchor_id,
        occurrence_plan.occurrence_id,
        occurrence_plan.template.context_id,
        occurrence_plan.template.arm,
        round_index,
        (
            None
            if predecessor_frontier is None
            else predecessor_frontier.frontier_id
        ),
        failed_audit.audit_id,
        frontier.frontier_id,
        model_pair.model_pair_id,
        model_replay_attestation.attestation_id,
        tuple(item.acquisition_id for item in acquisitions),
        tuple(sorted({item.row_binding_id for item in acquisitions})),
        candidates,
        source_recipe_id,
        decision,
        previous_draws,
    )


@dataclass(frozen=True, slots=True)
class RegisteredSelectorClosureV1:
    claim: RegisteredSelectorClaimV1
    independent_attestation: Any
    selection_authority: (
        accumulator.RegisteredAcquisitionSelectionAuthorityV1 | None
    )
    frontier: accumulator.RegisteredAcquisitionFrontierV1 | None
    _closure_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from acfqp import (
            v072_registered_target_selector_independent_verifier_v1
            as independent,
        )

        selected = (
            self.claim.decision.outcome
            is RegisteredSelectorOutcomeV1.SELECTED
        )
        if (
            type(self.claim) is not RegisteredSelectorClaimV1
            or type(self.independent_attestation)
            is not independent.RegisteredSelectorIndependentAttestationV1
            or self.independent_attestation.claim_id
            != self.claim.claim_id
            or selected
            != (
                type(self.selection_authority)
                is accumulator.RegisteredAcquisitionSelectionAuthorityV1
                and type(self.frontier)
                is accumulator.RegisteredAcquisitionFrontierV1
            )
            or (
                selected
                and self.frontier.selection_authority
                != self.selection_authority
            )
            or (
                not selected
                and (
                    self.selection_authority is not None
                    or self.frontier is not None
                )
            )
        ):
            raise V072RegisteredTargetSelectorInvariantViolation(
                "selector closure does not match independent replay"
            )
        object.__setattr__(
            self,
            "_closure_id",
            _content_id(
                "closure",
                {
                    "schema": "acfqp.v072_registered_selector_closure.v1",
                    "schema_version": SCHEMA_VERSION,
                    "claim_id": self.claim.claim_id,
                    "attestation_id": (
                        self.independent_attestation.attestation_id
                    ),
                    "selection_authority_id": (
                        None
                        if self.selection_authority is None
                        else self.selection_authority.selection_authority_id
                    ),
                    "frontier_id": (
                        None
                        if self.frontier is None
                        else self.frontier.frontier_id
                    ),
                    "outcome": self.claim.decision.outcome.value,
                },
            ),
        )

    @property
    def closure_id(self) -> str:
        return self._closure_id


def prepare_registered_acquisition_frontier_v1(
    *,
    authority_chain: consumer.RegisteredCampaignAuthorityChainV1,
    anchor: final_authority.V072RemoteMainAnchorV1,
    occurrence_plan: consumer.RegisteredOccurrenceExecutionPlanV1,
    failed_audit: robust.RobustPlanAuditV1,
    model_pair: models.RegisteredColdH2ModelPairV1,
    model_replay_attestation: (
        model_independent.RegisteredColdH2ModelIndependentReplayAttestationV1
    ),
    acquisitions: tuple[
        accumulator.RegisteredTargetRowAcquisitionV1, ...
    ],
    round_index: int,
    predecessor_frontier: (
        accumulator.RegisteredAcquisitionFrontierV1 | None
    ) = None,
) -> RegisteredSelectorClosureV1:
    """Prepare, independently replay, and freeze one registered frontier."""

    _validate_inputs(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        failed_audit=failed_audit,
        model_pair=model_pair,
        model_replay_attestation=model_replay_attestation,
        acquisitions=acquisitions,
        round_index=round_index,
        predecessor_frontier=predecessor_frontier,
    )
    claim = _build_claim(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        failed_audit=failed_audit,
        model_pair=model_pair,
        model_replay_attestation=model_replay_attestation,
        acquisitions=acquisitions,
        round_index=round_index,
        predecessor_frontier=predecessor_frontier,
    )
    from acfqp import (
        v072_registered_target_selector_independent_verifier_v1
        as independent,
    )

    attestation = independent.verify_registered_selector_independently_v1(
        authority_chain=authority_chain,
        anchor=anchor,
        occurrence_plan=occurrence_plan,
        failed_audit=failed_audit,
        model_pair=model_pair,
        model_replay_attestation=model_replay_attestation,
        acquisitions=acquisitions,
        round_index=round_index,
        predecessor_frontier=predecessor_frontier,
        claimed=claim,
    )
    if claim.decision.outcome is not RegisteredSelectorOutcomeV1.SELECTED:
        return RegisteredSelectorClosureV1(
            claim,
            attestation,
            None,
            None,
        )
    authority = (
        accumulator.mint_registered_acquisition_selection_authority_v1(
            selector_attestation=attestation,
            supporting_acquisitions=acquisitions,
        )
    )
    frontier = accumulator.freeze_registered_acquisition_frontier_v1(
        authority_chain=authority_chain,
        anchor=anchor,
        selection_authority=authority,
        predecessor=predecessor_frontier,
        supporting_acquisitions=acquisitions,
    )
    return RegisteredSelectorClosureV1(
        claim,
        attestation,
        authority,
        frontier,
    )


__all__ = [
    "GenericBoundaryCandidateV1",
    "GenericBoundarySelectionDecisionV1",
    "MAX_SELECTED_BOUNDARY_CANDIDATES_PER_ROUND",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "RegisteredBoundaryCandidateV1",
    "RegisteredNewChildRowSpecV1",
    "RegisteredSelectorClaimV1",
    "RegisteredSelectorClosureV1",
    "RegisteredSelectorGateLockedV1",
    "RegisteredSelectorOutcomeV1",
    "SCHEMA_VERSION",
    "V072RegisteredTargetSelectorInvariantViolation",
    "prepare_registered_acquisition_frontier_v1",
    "select_generic_boundary_candidate_core_v1",
]
